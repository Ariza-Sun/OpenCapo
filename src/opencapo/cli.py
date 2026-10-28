"""Command-line entry point used by developers and the pipeline worker."""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from opencapo import __version__
from opencapo.analysis.deps import require_analysis_packages
from opencapo.errors import InputError

if TYPE_CHECKING:
    from opencapo.analysis.beats import BeatTracker
    from opencapo.analysis.separate import Separator

AUDIO_EXTENSIONS = frozenset({".mp3", ".m4a", ".ogg", ".opus", ".wav", ".flac"})
DEVICES = ("auto", "cpu", "cuda")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="opencapo")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    analyze = commands.add_parser("analyze", help="analyze an audio file into JSON")
    analyze.add_argument("audio", type=Path, help="input audio file")
    analyze.add_argument("--out", required=True, help="output JSON path, or - for standard output")
    analyze.add_argument("--title", help="song title (default: file name)")
    analyze.add_argument("--artist", help="artist name")
    analyze.add_argument("--device", choices=DEVICES, default="auto", help="where models run")
    analyze.add_argument("--timing", help="write per-stage seconds as JSON here, or - for stderr")
    return parser


def check_input(audio: Path) -> None:
    if not audio.is_file():
        raise InputError(f"audio file not found: {audio}")
    if audio.suffix.lower() not in AUDIO_EXTENSIONS:
        supported = ", ".join(sorted(ext.lstrip(".") for ext in AUDIO_EXTENSIONS))
        raise InputError(f"unsupported audio format {audio.suffix!r}; use one of: {supported}")


def write_output(text: str, out: str) -> None:
    if out == "-":
        sys.stdout.write(text + "\n")
        return
    try:
        Path(out).write_text(text + "\n", encoding="utf-8")
    except OSError as e:
        raise InputError(f"cannot write {out}: {e.strerror}") from e


def main(
    argv: Sequence[str] | None = None,
    *,
    separator: "Separator | None" = None,
    tracker: "BeatTracker | None" = None,
) -> int:
    """Run the CLI. `separator` / `tracker` let tests inject fakes in place of the models."""
    args = build_parser().parse_args(argv)
    try:
        check_input(args.audio)
        # The analysis extra is checked before anything that imports it, so a
        # core-only install gets an install hint rather than an ImportError.
        if separator is None or tracker is None:
            require_analysis_packages()
        from opencapo.analysis.pipeline import analyze_file

        if separator is None:
            from opencapo.analysis.separate import DemucsSeparator

            separator = DemucsSeparator(device=args.device)
        if tracker is None:
            from opencapo.analysis.beats import BeatThisTracker

            tracker = BeatThisTracker(device=args.device)
        result = analyze_file(
            args.audio, separator=separator, tracker=tracker, title=args.title, artist=args.artist
        )
        write_output(result.analysis.to_json(), args.out)
        if args.timing:
            timing = json.dumps(result.timings.as_dict(), indent=2)
            if args.timing == "-":
                print(timing, file=sys.stderr)
            else:
                write_output(timing, args.timing)
    except InputError as e:
        print(f"opencapo: error: {e}", file=sys.stderr)
        return 1
    return 0
