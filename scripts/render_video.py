import argparse
import asyncio
import subprocess
import tempfile
from pathlib import Path

import edge_tts

VOICE = "en-US-AndrewNeural"
SUPPORTED = {".png", ".jpg", ".jpeg", ".webp"}


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-3000:])


async def make_voice(text: str, target: Path):
    await edge_tts.Communicate(text, voice=VOICE).save(str(target))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slides", default="assets/slides")
    parser.add_argument("--narration", required=True)
    parser.add_argument("--watermark", default="IELTS WINNERS")
    parser.add_argument("--seconds", type=int, default=5)
    parser.add_argument("--output", default="output/ielts-video.mp4")
    args = parser.parse_args()

    slide_dir = Path(args.slides)
    slides = sorted(p for p in slide_dir.iterdir() if p.suffix.lower() in SUPPORTED)
    if not slides:
        raise SystemExit(f"No slide images found in {slide_dir}")
    if args.seconds < 1 or args.seconds > 30:
        raise SystemExit("--seconds must be between 1 and 30")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        temp = Path(td)
        concat = temp / "slides.txt"
        with concat.open("w", encoding="utf-8") as f:
            for slide in slides:
                f.write(f"file '{slide.resolve().as_posix()}'\n")
                f.write(f"duration {args.seconds}\n")
            f.write(f"file '{slides[-1].resolve().as_posix()}'\n")

        silent = temp / "silent.mp4"
        audio = temp / "andrew-us.mp3"
        asyncio.run(make_voice(args.narration, audio))

        run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat),
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,"
                   "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=white,fps=30",
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            str(silent)
        ])
        run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(silent), "-i", str(audio),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-movflags", "+faststart", str(out)
        ])

    print(f"Created {out} using voice {VOICE}")


if __name__ == "__main__":
    main()
