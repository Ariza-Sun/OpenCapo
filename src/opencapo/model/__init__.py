"""Serialized data model shared by the pipeline, arranger and renderer."""

from opencapo.model.analysis import (
    SCHEMA_VERSION,
    TICKS_PER_BEAT,
    Analysis,
    Beat,
    Chord,
    Key,
    LyricSyllable,
    Note,
    Tempo,
)
from opencapo.model.arrangement import STRUM_AUTO, STRUM_NONE, TRANSPOSE_RANGE, Arrangement
from opencapo.model.music import ChordQuality, Mode

__all__ = [
    "SCHEMA_VERSION",
    "STRUM_AUTO",
    "STRUM_NONE",
    "TICKS_PER_BEAT",
    "TRANSPOSE_RANGE",
    "Analysis",
    "Arrangement",
    "Beat",
    "Chord",
    "ChordQuality",
    "Key",
    "LyricSyllable",
    "Mode",
    "Note",
    "Tempo",
]
