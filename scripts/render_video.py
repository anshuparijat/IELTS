import argparse
import asyncio
import subprocess
import tempfile
from pathlib import Path

import edge_tts

VOICE = "en-US-AndrewNeural"
SUPPORTED = {".gif"}


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-4000:])


async def make_voice(text: str, target: Path):
    await edge_tts.Communicate(text, voice=VOICE).save(str(target))


def duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True
    )
    return float(result.stdout.strip())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slides", required=True, help="Folder containing ordered GIF slides")
    parser.add_argument("--narration-file", required=True, help="One narration block per GIF, separated by a line containing ---")
    parser.add_argument("--output", default="output/ielts-video.mp4")
    args = parser.parse_args()

    slide_dir = Path(args.slides)
    gifs = sorted(p for p in slide_dir.iterdir() if p.suffix.lower() in SUPPORTED)
    if not gifs:
        raise SystemExit(f"No animated GIF slides found in {slide_dir}")

    narration_path = Path(args.narration_file)
    if not narration_path.is_file():
        raise SystemExit(f"Missing per-slide narration file: {narration_path}")
    raw = narration_path.read_text(encoding="utf-8")
    blocks = [b.strip() for b in raw.split("\\n---\\n") if b.strip()]
    if len(blocks) != len(gifs):
        raise SystemExit(f"Found {len(gifs)} GIFs but {len(blocks)} narration blocks. Add exactly one block per GIF, separated by a line containing ---.")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        temp = Path(td)
        segments = []
        for index, (gif, script) in enumerate(zip(gifs, blocks), start=1):
            audio = temp / f"voice-{index:03d}.mp3"
            segment = temp / f"segment-{index:03d}.mp4"
            asyncio.run(make_voice(script, audio))
            clip_duration = max(duration(gif), duration(audio) + 0.35)
            run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-stream_loop", "-1", "-i", str(gif), "-i", str(audio),
                "-t", f"{clip_duration:.3f}",
                "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,"
                       "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=white,fps=30,format=yuv420p",
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "libx264", "-preset", "veryfast",
                "-c:a", "aac", "-b:a", "192k", "-shortest",
                str(segment)
            ])
            segments.append(segment)

        concat = temp / "segments.txt"
        concat.write_text("".join(f"file '{p.as_posix()}'\\n" for p in segments), encoding="utf-8")
        run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat),
            "-c", "copy", "-movflags", "+faststart", str(out)
        ])

    print(f"Created {out} using {VOICE}; preserved GIF animation; no extra visual animation added.")


if __name__ == "__main__":
    main()
