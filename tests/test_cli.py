import subprocess
import sys
from pathlib import Path

import pytest

from opencapo.cli import main
from opencapo.model import Analysis

MAKE_TONE = Path(__file__).parents[1] / "scripts" / "make_tone.py"


def test_make_tone_script(tmp_path: Path) -> None:
    path = tmp_path / "tone.wav"
    subprocess.run([sys.executable, str(MAKE_TONE), str(path), "--seconds", "1"], check=True)
    assert path.stat().st_size > 44100


def test_analyze_writes_valid_json(tone: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.json"
    assert main(["analyze", str(tone), "--out", str(out)]) == 0
    result = Analysis.from_json(out.read_text(encoding="utf-8"))
    assert result.title == "Example Song"
    assert result.artist is None


def test_analyze_to_stdout(tone: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["analyze", str(tone), "--out", "-", "--title", "示例", "--artist", "X"]) == 0
    result = Analysis.from_json(capsys.readouterr().out)
    assert (result.title, result.artist) == ("示例", "X")


def test_extension_is_case_insensitive(tmp_path: Path) -> None:
    audio = tmp_path / "song.MP3"
    audio.write_bytes(b"")
    assert main(["analyze", str(audio), "--out", str(tmp_path / "out.json")]) == 0


def test_missing_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["analyze", str(tmp_path / "nope.mp3"), "--out", "-"]) == 1
    assert "audio file not found" in capsys.readouterr().err


def test_unsupported_format(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    audio = tmp_path / "song.mid"
    audio.write_bytes(b"")
    assert main(["analyze", str(audio), "--out", "-"]) == 1
    err = capsys.readouterr().err
    assert "unsupported audio format '.mid'" in err
    assert "mp3" in err


def test_unwritable_output(tone: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "missing-dir" / "out.json"
    assert main(["analyze", str(tone), "--out", str(out)]) == 1
    assert "cannot write" in capsys.readouterr().err


@pytest.mark.parametrize("argv", [[], ["analyze"], ["analyze", "song.mp3"]])
def test_usage_errors_exit_2(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 2


def test_module_entry_point(tone: Path) -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "opencapo", "analyze", str(tone), "--out", "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert Analysis.from_json(proc.stdout).title == tone.stem
