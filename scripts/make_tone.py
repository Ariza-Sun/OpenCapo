"""Write a short synthetic WAV (a sine tone) for smoke-testing the CLI.

Usage: python scripts/make_tone.py OUT.wav [--seconds 3]

The repository ships no real recordings; tests and CI generate this instead.
"""

import argparse
import math
import struct
import wave

SAMPLE_RATE = 44100
FREQUENCY = 440.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out")
    parser.add_argument("--seconds", type=float, default=3.0)
    args = parser.parse_args()

    n = int(args.seconds * SAMPLE_RATE)
    frames = b"".join(
        struct.pack("<h", int(0.3 * 32767 * math.sin(2 * math.pi * FREQUENCY * i / SAMPLE_RATE)))
        for i in range(n)
    )
    with wave.open(args.out, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(frames)


if __name__ == "__main__":
    main()
