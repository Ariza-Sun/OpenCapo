"""Rule expert E5: key, estimated two ways and cross-checked.

Way one listens to the whole piece: the average chroma is correlated with
the Krumhansl-Schmuckler key profiles. Way two reads the chord sheet: each
candidate key is scored by how much of the chord sequence (by duration) it
explains. A transcriber does both ("the song sits on G, and these chords are
the ones G major has"), and when the two disagree the key is doubtful.

Key index convention: tonic * 2 + (0 for major, 1 for minor).
"""

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from opencapo.analysis.chords.fusion import MAJOR_SCALE, MINOR_SCALE
from opencapo.analysis.chords.vocab import chord_tones
from opencapo.model import Chord, ChordQuality, Key, Mode

# Krumhansl & Kessler (1982) probe-tone profiles.
KS_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KS_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

MAJOR_FAMILY = frozenset(
    {ChordQuality.MAJ, ChordQuality.MAJ7, ChordQuality.MAJ6, ChordQuality.DOM7}
)
MINOR_FAMILY = frozenset({ChordQuality.MIN, ChordQuality.MIN7, ChordQuality.MIN6})


def key_index(tonic: int, mode: Mode) -> int:
    return tonic * 2 + (0 if mode == Mode.MAJOR else 1)


def key_from_index(index: int) -> tuple[int, Mode]:
    return index // 2, Mode.MAJOR if index % 2 == 0 else Mode.MINOR


def scale_of(tonic: int, mode: Mode) -> frozenset[int]:
    degrees = MAJOR_SCALE if mode == Mode.MAJOR else (*MINOR_SCALE, 11)  # harmonic minor's 7th
    return frozenset((tonic + d) % 12 for d in degrees)


def scores_from_chroma(mean_chroma: NDArray[np.float64]) -> NDArray[np.float64]:
    """(24,) Pearson correlation of the chroma with each rotated profile."""
    scores = np.zeros(24)
    if not np.any(mean_chroma):
        return scores
    for tonic in range(12):
        for mode, profile in ((Mode.MAJOR, KS_MAJOR), (Mode.MINOR, KS_MINOR)):
            rotated = np.roll(profile, tonic)
            scores[key_index(tonic, mode)] = float(np.corrcoef(mean_chroma, rotated)[0, 1])
    return scores


def scores_from_chords(chords: Sequence[Chord]) -> NDArray[np.float64]:
    """(24,) duration-weighted share of the chord sequence each key explains.

    A chord counts fully when all its tones are in the key, half when only
    its root is; the tonic chord of the right quality family earns a bonus.
    """
    scores = np.zeros(24)
    total = sum(c.end - c.start for c in chords)
    if total <= 0:
        return scores
    for index in range(24):
        tonic, mode = key_from_index(index)
        scale = scale_of(tonic, mode)
        family = MAJOR_FAMILY if mode == Mode.MAJOR else MINOR_FAMILY
        value = 0.0
        for chord in chords:
            duration = chord.end - chord.start
            tones = chord_tones(chord.root, chord.quality)
            if tones <= scale:
                value += duration
            elif chord.root in scale:
                value += 0.5 * duration
            if chord.root == tonic and chord.quality in family:
                value += 0.5 * duration
        scores[index] = value / (1.5 * total)
    return scores


def _normalise(scores: NDArray[np.float64]) -> NDArray[np.float64]:
    shifted = scores - scores.min()
    total = shifted.sum()
    return np.asarray(shifted / total) if total > 0 else np.full(24, 1 / 24)


def estimate_key(
    chroma_scores: NDArray[np.float64],
    chord_scores: NDArray[np.float64],
    chords: Sequence[Chord] = (),
) -> Key | None:
    """Combine both views; None when neither has any evidence.

    Confidence is the margin between the best and second-best key, halved
    when the two views disagree on the winner. A relative-major/minor tie
    (same scale) is settled by which of the I and vi chords lasts longer.
    """
    has_chroma, has_chords = bool(np.any(chroma_scores)), bool(np.any(chord_scores))
    if not has_chroma and not has_chords:
        return None
    combined = np.zeros(24)
    if has_chroma:
        combined += _normalise(chroma_scores)
    if has_chords:
        combined += _normalise(chord_scores)
    order = np.argsort(combined)[::-1]
    best, second = int(order[0]), int(order[1])
    if _relative_pair(best, second) and abs(combined[best] - combined[second]) < 1e-3:
        best, second = _settle_relative(best, second, chords)
    margin = (combined[best] - combined[second]) / max(combined[best], 1e-9)
    confidence = float(min(1.0, 6.0 * margin))  # a 1/6 relative margin is already clear
    if has_chroma and has_chords and int(np.argmax(chroma_scores)) != int(np.argmax(chord_scores)):
        confidence /= 2.0
    tonic, mode = key_from_index(best)
    return Key(tonic=tonic, mode=mode, confidence=confidence)


def _relative_pair(a: int, b: int) -> bool:
    ta, ma = key_from_index(a)
    tb, mb = key_from_index(b)
    if ma == mb:
        return False
    major, minor = (ta, tb) if ma == Mode.MAJOR else (tb, ta)
    return (major + 9) % 12 == minor


def _settle_relative(a: int, b: int, chords: Sequence[Chord]) -> tuple[int, int]:
    ta, ma = key_from_index(a)
    tb, _ = key_from_index(b)
    major_tonic = ta if ma == Mode.MAJOR else tb
    minor_tonic = (major_tonic + 9) % 12
    major_time = sum(
        c.end - c.start for c in chords if c.root == major_tonic and c.quality in MAJOR_FAMILY
    )
    minor_time = sum(
        c.end - c.start for c in chords if c.root == minor_tonic and c.quality in MINOR_FAMILY
    )
    major_index = key_index(major_tonic, Mode.MAJOR)
    minor_index = key_index(minor_tonic, Mode.MINOR)
    return (minor_index, major_index) if minor_time > major_time else (major_index, minor_index)
