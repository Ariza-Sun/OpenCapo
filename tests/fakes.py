"""Stand-ins for the model adapters so the pipeline runs on CPU without weights."""

import numpy as np

from opencapo.analysis.audio import Audio
from opencapo.analysis.beats import BeatTimes
from opencapo.analysis.separate import STEM_NAMES, Stems


class FakeSeparator:
    """Puts the whole mix into `other`; the rest is silence."""

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    def separate(self, audio: Audio) -> Stems:
        self.calls += 1
        if self.fail:
            raise RuntimeError("separator crashed")
        silence = np.zeros_like(audio.samples)
        return Stems(
            sample_rate=audio.sample_rate,
            **{name: silence for name in STEM_NAMES if name != "other"},
            other=audio.samples,
        )


class FakeTracker:
    """Evenly spaced beats at a fixed BPM, four per bar, from time 0."""

    def __init__(self, bpm: float = 120.0, beats_per_bar: int = 4) -> None:
        self.bpm = bpm
        self.beats_per_bar = beats_per_bar
        self.inputs: list[Audio] = []

    def track(self, audio: Audio) -> BeatTimes:
        self.inputs.append(audio)
        beats = np.arange(0.0, audio.duration, 60.0 / self.bpm)
        return BeatTimes(beats=beats, downbeats=beats[:: self.beats_per_bar])
