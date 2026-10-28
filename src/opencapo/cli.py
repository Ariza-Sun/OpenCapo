"""Command-line entry point used by developers and the pipeline worker."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from opencapo import __version__
from opencapo.errors import InputError
from opencapo.model import Analysis

AUDIO_EXTENSIONS = frozenset({".mp3", ".m4a", ".ogg", ".opus", ".wav", ".flac"})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="opencapo")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    analyze = commands.add_parser("analyze", help="analyze an audio file into JSON")
    analyze.add_argument("audio", type=Path, help="input audio file")
    analyze.add_argument("--out", required=True, help="output JSON path, or - for standard output")
    analyze.add_argument("--title", help="song title (default: file name)")
    analyze.add_argument("--artist", help="artist name")
    return parser


def analyze(audio: Path, title: str | None, artist: str | None) -> Analysis:
    if not audio.is_file():
        raise InputError(f"audio file not found: {audio}")
    if audio.suffix.lower() not in AUDIO_EXTENSIONS:
        supported = ", ".join(sorted(ext.lstrip(".") for ext in AUDIO_EXTENSIONS))
        raise InputError(f"unsupported audio format {audio.suffix!r}; use one of: {supported}")
    # No analysis stages exist yet; they are added from roadmap step 1 onwards.
    return Analysis(title=title or audio.stem, artist=artist)


def write_output(text: str, out: str) -> None:
    if out == "-":
        sys.stdout.write(text + "\n")
        return
    try:
        Path(out).write_text(text + "\n", encoding="utf-8")
    except OSError as e:
        raise InputError(f"cannot write {out}: {e.strerror}") from e


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = analyze(args.audio, args.title, args.artist)
        write_output(result.to_json(), args.out)
    except InputError as e:
        print(f"opencapo: error: {e}", file=sys.stderr)
        return 1
    return 0
