"""The analysis pipeline: decode, separate, track beats, build the grid.

Stages are injected as protocols so the pipeline itself runs under test with
fakes; the real adapters live in `separate.py` and `beats.py`.
"""

import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from opencapo.analysis.audio import decode
from opencapo.analysis.beats import BeatTracker
from opencapo.analysis.grid import build_grid
from opencapo.analysis.separate import Separator, stems_workdir
from opencapo.model import Analysis

BeatInput = Literal["mix", "drums_bass"]


@dataclass
class StageTimings:
    """Seconds spent in each stage; `total` covers everything including setup."""

    decode: float = 0.0
    separate: float = 0.0
    beats: float = 0.0
    total: float = 0.0
    extra: dict[str, float] = field(default_factory=dict)

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            if name in ("decode", "separate", "beats", "total"):
                setattr(self, name, getattr(self, name) + elapsed)
            else:
                self.extra[name] = self.extra.get(name, 0.0) + elapsed

    def as_dict(self) -> dict[str, float]:
        return {
            "decode": self.decode,
            "separate": self.separate,
            "beats": self.beats,
            **self.extra,
            "total": self.total,
        }


@dataclass(frozen=True)
class AnalysisResult:
    analysis: Analysis
    timings: StageTimings


def analyze_file(
    path: Path,
    *,
    separator: Separator,
    tracker: BeatTracker,
    title: str | None = None,
    artist: str | None = None,
    beat_input: BeatInput = "mix",
) -> AnalysisResult:
    """Run every step-1 stage on one file. Stems never outlive this call."""
    timings = StageTimings()
    with timings.stage("total"):
        with timings.stage("decode"):
            audio = decode(path)
        with stems_workdir() as workdir:
            with timings.stage("separate"):
                stems = separator.separate(audio)
                stems.write(workdir)
            with timings.stage("beats"):
                tracked = tracker.track(
                    stems.mix("drums", "bass") if beat_input == "drums_bass" else audio
                )
        grid = build_grid(tracked.beats.tolist(), tracked.downbeats.tolist())
        analysis = Analysis(
            title=title or path.stem,
            artist=artist,
            duration=audio.duration,
            beats=grid.beats,
            tempo=grid.tempo,
            time_signature=grid.time_signature,
        )
    return AnalysisResult(analysis=analysis, timings=timings)
