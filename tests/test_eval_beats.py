"""The evaluation script's loaders and metric glue, without any model."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "eval_beats.py"
spec = importlib.util.spec_from_file_location("eval_beats", SCRIPT)
assert spec and spec.loader
eval_beats = importlib.util.module_from_spec(spec)
sys.modules["eval_beats"] = eval_beats
spec.loader.exec_module(eval_beats)

mir_eval_missing = importlib.util.find_spec("mir_eval") is None


def test_parse_beats_file(tmp_path: Path) -> None:
    path = tmp_path / "gtzan_blues_00000.beats"
    path.write_text(
        "0.217\t3\n0.695\t4\n1.173\t1\n1.653\t2\n# comment\n2.137\t3.0\n", encoding="utf-8"
    )
    beats, downbeats = eval_beats.parse_beats_file(path)
    np.testing.assert_allclose(beats, [0.217, 0.695, 1.173, 1.653, 2.137])
    np.testing.assert_allclose(downbeats, [1.173])


def test_load_tracks_matches_both_layouts(tmp_path: Path) -> None:
    audio = tmp_path / "audio"
    (audio / "genres_original" / "blues").mkdir(parents=True)
    (audio / "genres_original" / "blues" / "blues.00000.wav").write_bytes(b"")
    (audio / "genres" / "rock").mkdir(parents=True)
    (audio / "genres" / "rock" / "rock.00007.au").write_bytes(b"")
    (audio / "genres" / "pop").mkdir(parents=True)
    (audio / "genres" / "pop" / "pop.00001.wav").write_bytes(b"")
    ann = tmp_path / "beats"
    ann.mkdir()
    for name in ("gtzan_blues_00000.beats", "gtzan_rock_00007.beats", "gtzan_jazz_00054.beats"):
        (ann / name).write_text("1.0\t1\n2.0\t2\n", encoding="utf-8")
    (ann / "gtzan_pop_00001.beats").write_text("", encoding="utf-8")
    (ann / "weird.beats").write_text("1.0\t1\n", encoding="utf-8")

    tracks, problems = eval_beats.load_tracks(audio, ann)
    assert [t.name for t in tracks] == ["blues.00000", "rock.00007"]
    assert tracks[1].audio.suffix == ".au"
    assert any("jazz_00054" in p for p in problems)  # no audio
    assert any("weird.beats" in p for p in problems)  # bad name
    assert any(p == "empty annotation: gtzan_pop_00001.beats" for p in problems)


def test_load_tracks_with_nothing(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    tracks, problems = eval_beats.load_tracks(tmp_path / "a", tmp_path / "b")
    assert tracks == [] and problems[-1].startswith("no tracks matched")


@pytest.mark.skipif(mir_eval_missing, reason="mir_eval not installed")
def test_score_trims_the_first_five_seconds() -> None:
    reference = np.arange(0.0, 30.0, 0.5)
    assert eval_beats.score(reference, reference) == 1.0
    # Wrong in the first 5 s only: trimmed away, still perfect.
    estimate = np.concatenate([np.arange(0.1, 5.0, 0.3), reference[reference >= 5.0]])
    assert eval_beats.score(reference, estimate) == 1.0
    # Half the beats missing after 5 s: F1 = 2PR/(P+R) with P=1, R=0.5.
    assert eval_beats.score(reference, reference[::2]) == pytest.approx(2 / 3, abs=0.02)
    assert np.isnan(eval_beats.score(np.array([1.0, 2.0]), reference))


@pytest.mark.skipif(mir_eval_missing, reason="mir_eval not installed")
def test_self_check_and_summary(tmp_path: Path) -> None:
    beats = np.arange(0.0, 30.0, 0.5)
    track = eval_beats.Track("rock", "00001", tmp_path / "x.wav", beats, beats[::4])
    summary = eval_beats.evaluate("annotations", None, [track])
    assert summary.mean("beat_f1") == 1.0 and summary.mean("downbeat_f1") == 1.0
    assert summary.as_dict()["by_genre"]["rock"]["beat_f1"] == 1.0
    assert np.isnan(summary.mean("beat_f1", "jazz"))


def test_markdown_marks_acceptance() -> None:
    rows = [eval_beats.Row("rock.00001", "rock", 0.9, 0.7, 0.1)]
    good = eval_beats.Summary("beat_this", rows)
    bad = eval_beats.Summary("other", [eval_beats.Row("rock.00001", "rock", 0.5, 0.2, 0.1)])
    env = {"date": "2026-01-01", "python": "3.12", "device": "cpu", "packages": {"torch": "2"}}
    text = eval_beats.markdown([good, bad], env, ["no audio for x"], 1)
    assert "| beat_this | 0.900 | 0.700 | 0.10 | 通过 |" in text
    assert "| other | 0.500 | 0.200 | 0.10 | 未通过 |" in text
    assert "- no audio for x" in text
