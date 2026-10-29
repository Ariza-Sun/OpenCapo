"""The chord evaluation script's loaders and scoring glue, without any model."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from conftest import write_tone

SCRIPT = Path(__file__).parents[1] / "scripts" / "eval_chords.py"
spec = importlib.util.spec_from_file_location("eval_chords", SCRIPT)
assert spec and spec.loader
eval_chords = importlib.util.module_from_spec(spec)
sys.modules["eval_chords"] = eval_chords
spec.loader.exec_module(eval_chords)

mir_eval_missing = importlib.util.find_spec("mir_eval") is None


def jams_file(
    path: Path, *, chords: list[tuple[float, float, str]], key: str, beats: list[float]
) -> None:
    def ann(namespace: str, data: list[dict]) -> dict:
        return {
            "namespace": namespace,
            "annotation_metadata": {"data_source": "test"},
            "data": data,
        }

    chord_obs = [{"time": t, "duration": d, "value": v, "confidence": None} for t, d, v in chords]
    beat_obs = [
        {
            "time": t,
            "duration": 0.0,
            "value": {"position": i % 4 + 1, "measure": i // 4},
            "confidence": None,
        }
        for i, t in enumerate(beats)
    ]
    jam = {
        "annotations": [
            ann("chord", chord_obs),
            ann("chord", chord_obs[:1]),  # the "performed" version
            ann("key_mode", [{"time": 0.0, "duration": 30.0, "value": key, "confidence": None}]),
            ann("beat_position", beat_obs),
        ],
        "file_metadata": {"duration": 30.0},
    }
    path.write_text(json.dumps(jam), encoding="utf-8")


def test_guitarset_loader(tmp_path: Path) -> None:
    root = tmp_path / "guitarset"
    (root / "annotation").mkdir(parents=True)
    (root / "audio_mono-mic").mkdir()
    for name in ("00_BN1-129-Eb_comp", "03_Rock2-142-D_solo"):
        jams_file(
            root / "annotation" / f"{name}.jams",
            chords=[(0.0, 2.0, "C:maj"), (2.0, 2.0, "G:maj/3")],
            key="C:major",
            beats=[0.0, 0.5, 1.0, 1.5, 2.0],
        )
        write_tone(root / "audio_mono-mic" / f"{name}_mic.wav", seconds=0.2)
    tracks = eval_chords.guitarset_tracks(root)
    assert [t.name for t in tracks] == ["00_BN1-129-Eb_comp", "03_Rock2-142-D_solo"]
    assert [t.split for t in tracks] == ["tune", "report"]
    assert [t.group for t in tracks] == ["BN", "Ro"]
    first = tracks[0]
    assert first.chord_labels == ["C:maj", "G:maj/3"]
    np.testing.assert_allclose(first.chord_intervals, [[0.0, 2.0], [2.0, 4.0]])
    assert first.key == (0, "major")
    assert first.beats.tolist() == [0.0, 0.5, 1.0, 1.5, 2.0] and first.downbeats.tolist() == [
        0.0,
        2.0,
    ]
    performed = eval_chords.guitarset_tracks(root, chords="performed")
    assert performed[0].chord_labels == ["C:maj"]


def test_jams_dict_of_lists_form() -> None:
    ann = {
        "data": {
            "time": [0.0, 1.0],
            "duration": [1.0, 1.0],
            "value": ["C:maj", "N"],
            "confidence": [None, None],
        }
    }
    obs = eval_chords.jams_observations(ann)
    assert obs[1] == {"time": 1.0, "duration": 1.0, "value": "N", "confidence": None}


def test_arff_reader_and_aam_loader(tmp_path: Path) -> None:
    root = tmp_path / "aam"
    (root / "0001").mkdir(parents=True)
    (root / "0001" / "0001_chords.arff").write_text(
        "@RELATION chords\n@ATTRIBUTE 'Onset in seconds' NUMERIC\n"
        "@ATTRIBUTE 'Offset in seconds' NUMERIC\n@ATTRIBUTE Chord STRING\n"
        "@DATA\n0.0,2.0,'C:maj'\n2.0,4.0,Am\n4.0,6.0,'G7'\n",
        encoding="utf-8",
    )
    (root / "0001" / "0001_key.arff").write_text(
        "@RELATION key\n@ATTRIBUTE 'Key' STRING\n@DATA\n'A minor'\n", encoding="utf-8"
    )
    (root / "0001" / "0001_beats.arff").write_text(
        "@RELATION beats\n@ATTRIBUTE 'Onset in seconds' NUMERIC\n"
        "@ATTRIBUTE 'Beat position' NUMERIC\n@DATA\n0.0,1\n0.5,2\n1.0,3\n1.5,4\n2.0,1\n",
        encoding="utf-8",
    )
    write_tone(root / "0001" / "0001_mix.wav", seconds=0.2)
    (root / "0002").mkdir()
    (root / "0002" / "0002_chords.arff").write_text(
        "@RELATION c\n@ATTRIBUTE Onset NUMERIC\n@ATTRIBUTE Chord STRING\n@DATA\n0.0,C\n",
        encoding="utf-8",
    )
    tracks = eval_chords.aam_tracks(root, count=500)
    assert [t.name for t in tracks] == ["0001"]  # 0002 has no audio and is skipped
    t = tracks[0]
    assert t.chord_labels == ["C:maj", "A:min", "G:7"]
    np.testing.assert_allclose(t.chord_intervals, [[0, 2], [2, 4], [4, 6]])
    assert t.key == (9, "minor")
    assert t.beats.tolist() == [0.0, 0.5, 1.0, 1.5, 2.0] and t.downbeats.tolist() == [0.0, 2.0]
    assert eval_chords.aam_tracks(root, count=0) == []


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("A:minor", (9, "minor")),
        ("Eb:major", (3, "major")),
        ("F# minor", (6, "minor")),
        ("Cm", (0, "minor")),
        ("G", (7, "major")),
        ("N", None),
        ("??", None),
    ],
)
def test_parse_key(text: str, expected: tuple[int, str] | None) -> None:
    assert eval_chords.parse_key(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("C", "C:maj"),
        ("Am", "A:min"),
        ("G7", "G:7"),
        ("Bbm7", "Bb:min7"),
        ("F#dim", "F#:dim"),
        ("N", "N"),
        ("D:maj/3", "D:maj/3"),
        ("Cm7b5", "C:hdim7"),
    ],
)
def test_normalize_aam_label(text: str, expected: str) -> None:
    assert eval_chords.normalize_aam_label(text) == expected


@pytest.mark.skipif(mir_eval_missing, reason="mir_eval not installed")
def test_chord_scores_self_check_and_gaps() -> None:
    ref = np.array([[0.0, 2.0], [2.0, 4.0]])
    labels = ["C:maj", "G:maj/3"]
    perfect = eval_chords.chord_scores(ref, labels, ref, labels)
    assert all(perfect[m] == 1.0 for m in eval_chords.CHORD_METRICS)
    # An estimate covering only the first half: majmin credit for half the time.
    half = eval_chords.chord_scores(ref, labels, np.array([[0.0, 2.0]]), ["C:maj"])
    assert half["majmin"] == pytest.approx(0.5)
    # Ignoring the inversion costs the _inv metrics but not majmin.
    no_inv = eval_chords.chord_scores(ref, labels, ref, ["C:maj", "G:maj"])
    assert no_inv["majmin"] == 1.0 and no_inv["majmin_inv"] == pytest.approx(0.5)
    assert np.isnan(eval_chords.chord_scores(np.zeros((0, 2)), [], ref, labels)["majmin"])


@pytest.mark.skipif(mir_eval_missing, reason="mir_eval not installed")
def test_key_scores() -> None:
    assert eval_chords.key_scores((0, "major"), (0, "major")) == {
        "key_exact": 1.0,
        "key_weighted": 1.0,
    }
    relative = eval_chords.key_scores((0, "major"), (9, "minor"))
    assert relative["key_exact"] == 0.0 and 0.0 < relative["key_weighted"] < 1.0
    assert eval_chords.key_scores((0, "major"), None) == {"key_exact": 0.0, "key_weighted": 0.0}
    assert np.isnan(eval_chords.key_scores(None, (0, "major"))["key_exact"])


def test_summarize_splits_by_dataset_and_group() -> None:
    rows = [
        {
            "track": "a",
            "dataset": "guitarset",
            "split": "tune",
            "group": "BN",
            "majmin": 0.8,
            "sevenths": 0.7,
            "majmin_inv": 0.8,
            "sevenths_inv": 0.7,
            "root": 0.9,
            "key_exact": 1.0,
            "key_weighted": 1.0,
            "seconds": 1.0,
        },
        {
            "track": "b",
            "dataset": "guitarset",
            "split": "report",
            "group": "Ro",
            "majmin": 0.6,
            "sevenths": 0.5,
            "majmin_inv": 0.6,
            "sevenths_inv": 0.5,
            "root": 0.7,
            "key_exact": 0.0,
            "key_weighted": 0.5,
            "seconds": 2.0,
        },
        {
            "track": "c",
            "dataset": "aam",
            "split": "report",
            "group": "aam",
            "majmin": 0.9,
            "sevenths": 0.9,
            "majmin_inv": 0.9,
            "sevenths_inv": 0.9,
            "root": 0.9,
            "key_exact": 1.0,
            "key_weighted": 1.0,
            "seconds": 3.0,
        },
    ]
    summary = eval_chords.summarize({"rows": rows})
    assert summary["guitarset_tune"]["majmin"] == 0.8 and summary["guitarset_tune"]["tracks"] == 1
    assert summary["guitarset_report"]["key_exact"] == 0.0
    assert summary["aam"]["seconds"] == 3.0
    text = eval_chords.markdown(
        [{"system": "x", "summary": summary, "params": {}, "rows": rows}],
        {"date": "2026-01-01", "python": "3", "device": "cpu", "packages": {}},
        ["note"],
    )
    assert "| x | 0.600 |" in text and "未通过" in text and "- note" in text
