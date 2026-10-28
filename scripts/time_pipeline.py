"""Per-stage timing of the analysis pipeline on one song (step-1 acceptance).

Usage:
    python scripts/time_pipeline.py SONG.mp3 [--device auto] [--repeat 3] \
        [--separators htdemucs,htdemucs_ft] [--out docs/benchmarks/step-1-timing]

The first run of each configuration is reported separately as "cold" (it
includes loading weights); the acceptance number is the median of the warm
runs. Model inference time depends on length, not content, so any ~4 minute
song will do; the song itself is not committed. Writes OUT.json and OUT.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.metadata
import json
import platform
import statistics
from pathlib import Path

ACCEPTANCE_SECONDS = 90.0


def run_once(song: Path, model: str, device: str, separator_cache: dict) -> dict[str, float]:
    from opencapo.analysis.beats import BeatThisTracker
    from opencapo.analysis.pipeline import analyze_file
    from opencapo.analysis.separate import DemucsSeparator

    if model not in separator_cache:
        separator_cache[model] = DemucsSeparator(model=model, device=device)
    if "tracker" not in separator_cache:
        separator_cache["tracker"] = BeatThisTracker(device=device)
    result = analyze_file(
        song, separator=separator_cache[model], tracker=separator_cache["tracker"]
    )
    timings = result.timings.as_dict()
    timings["beats_found"] = len(result.analysis.beats)
    timings["bpm"] = result.analysis.tempo.bpm if result.analysis.tempo else float("nan")
    return timings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("song", type=Path)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--repeat", type=int, default=3, help="warm runs per configuration")
    parser.add_argument("--separators", default="htdemucs,htdemucs_ft")
    parser.add_argument("--out", default="docs/benchmarks/step-1-timing")
    args = parser.parse_args(argv)

    from opencapo.analysis.audio import probe
    from opencapo.analysis.device import resolve_device

    device = resolve_device(args.device)
    duration = probe(args.song).duration
    cache: dict = {}
    results = []
    for model in args.separators.split(","):
        cold = run_once(args.song, model, device, cache)
        warm = [run_once(args.song, model, device, cache) for _ in range(args.repeat)]
        stages = ["decode", "separate", "beats", "total"]
        results.append(
            {
                "separator": model,
                "cold": cold,
                "warm_runs": warm,
                "warm_median": {k: statistics.median(r[k] for r in warm) for k in stages},
                "beats_found": warm[-1]["beats_found"],
                "bpm": warm[-1]["bpm"],
            }
        )
        print(model, json.dumps(results[-1]["warm_median"]))

    env = {
        "date": dt.date.today().isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "device": device,
        "packages": {
            n: importlib.metadata.version(n) for n in ("opencapo", "torch", "demucs", "beat-this")
        },
    }
    import torch

    if device.startswith("cuda") and torch.cuda.is_available():
        env["gpu"] = torch.cuda.get_device_name(0)

    payload = {
        "environment": env,
        "song": {"name": args.song.name, "duration_seconds": duration},
        "acceptance_total_seconds": ACCEPTANCE_SECONDS,
        "results": results,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    minutes, seconds = divmod(round(duration), 60)
    lines = [
        "# 第 1 步：耗时（分轨 + 节拍）",
        "",
        f"由 `scripts/time_pipeline.py` 生成于 {env['date']}。",
        f"设备：{env.get('gpu') or device}；Python {env['python']}；"
        + "、".join(f"{k} {v}" for k, v in env["packages"].items()),
        "",
        f"歌曲时长 {minutes}:{seconds:02d}（文件不提交）。每个配置先跑 1 次冷启动（含加载权重），"
        f"再跑 {args.repeat} 次取中位数。验收：4 分钟歌曲分轨 + 节拍 ≤ {ACCEPTANCE_SECONDS:.0f} 秒"
        "（看 `htdemucs` 行的热启动合计）。",
        "",
        "| 分轨模型 | 解码 | 分轨 | 节拍 | 合计（热） | 合计（冷） | 验收 |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        w, c = r["warm_median"], r["cold"]
        verdict = "通过" if w["total"] <= ACCEPTANCE_SECONDS else "未通过"
        if r["separator"] != "htdemucs":
            verdict = "参考"
        cells = [
            r["separator"],
            f"{w['decode']:.1f} s",
            f"{w['separate']:.1f} s",
            f"{w['beats']:.1f} s",
            f"**{w['total']:.1f} s**",
            f"{c['total']:.1f} s",
            verdict,
        ]
        lines.append("| " + " | ".join(cells) + " |")
    out.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out.with_suffix(".md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
