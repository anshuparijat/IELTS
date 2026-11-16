import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, FileResponse
from PIL import Image, ImageDraw, ImageFont, ImageOps

APP_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MAX_SLIDES = 30
MAX_UPLOAD_BYTES = 40 * 1024 * 1024
ALLOWED_IMAGES = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_AUDIO = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}

app = FastAPI(title="IELTS AI Video Renderer", version="0.1.0")


def run_ffmpeg(args: list[str]) -> None:
    try:
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args],
            capture_output=True, text=True, check=False
        )
    except FileNotFoundError as exc:
        raise HTTPException(500, "FFmpeg is not installed on this server.") from exc
    if proc.returncode != 0:
        raise HTTPException(500, f"Video rendering failed: {proc.stderr[-2500:]}")


def font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/Library/Fonts/Arial Bold.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def make_slide(source: Path, destination: Path, width: int, height: int,
               heading: str, caption: str, watermark: str) -> None:
    image = Image.open(source).convert("RGB")
    image = ImageOps.contain(image, (width, height), method=Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (width, height), "#f7f6f2")
    canvas.paste(image, ((width - image.width) // 2, (height - image.height) // 2))
    draw = ImageDraw.Draw(canvas)

    if heading.strip():
        f = font(max(28, width // 22))
        text = heading.strip()[:100]
        bbox = draw.textbbox((0, 0), text, font=f)
        pad = 24
        box_w = min(width - 64, bbox[2] - bbox[0] + pad * 2)
        draw.rounded_rectangle((32, 28, 32 + box_w, 28 + bbox[3] - bbox[1] + pad * 2),
                               radius=18, fill="#ffffff", outline="#222222", width=2)
        draw.text((32 + pad, 28 + pad), text, font=f, fill="#111111")

    if caption.strip():
        f = font(max(24, width // 30))
        text = caption.strip()[:220]
        margin = 42
        max_width = width - margin * 2
        words, lines, line = text.split(), [], ""
        for word in words:
            candidate = f"{line} {word}".strip()
            if draw.textbbox((0, 0), candidate, font=f)[2] <= max_width:
                line = candidate
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)
        lines = lines[:3]
        line_h = f.size + 12
        panel_h = len(lines) * line_h + 34
        top = height - panel_h - 42
        draw.rounded_rectangle((24, top, width - 24, height - 24), radius=16,
                               fill="#ffffff", outline="#222222", width=2)
        for i, line in enumerate(lines):
            draw.text((margin, top + 16 + i * line_h), line, font=f, fill="#111111")

    if watermark.strip():
        wf = font(max(16, width // 65))
        label = watermark.strip()[:45]
        bbox = draw.textbbox((0, 0), label, font=wf)
        x = width - bbox[2] - 28
        y = height - bbox[3] - 18
        draw.text((x, y), label, font=wf, fill="#555555")

    canvas.save(destination, quality=94)


@app.get("/health")
def health():
    return {"status": "ok", "renderer": "ffmpeg", "version": app.version}


@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse("""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>IELTS AI Video Renderer</title>
<style>
body{font:16px Arial,sans-serif;background:#f4f4f1;color:#171717;margin:0;padding:32px}
main{max-width:760px;margin:auto;background:white;padding:28px;border:1px solid #ddd;border-radius:14px}
h1{font-size:26px}label{display:block;font-weight:700;margin:18px 0 7px}
input,textarea,select{width:100%;box-sizing:border-box;padding:12px;border:1px solid #aaa;border-radius:7px}
button{margin-top:22px;background:#171717;color:white;padding:13px 20px;border:0;border-radius:7px;font-weight:700;cursor:pointer}
small{color:#555}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:600px){.grid{grid-template-columns:1fr}body{padding:12px}main{padding:18px}}
</style></head><body><main>
<h1>IELTS AI Video Renderer</h1>
<p>Upload slide images, add optional narration and render a downloadable MP4.</p>
<form action="/render" method="post" enctype="multipart/form-data">
<label>Slide images (PNG, JPG or WEBP; select in display order)</label><input name="slides" type="file" accept="image/png,image/jpeg,image/webp" multiple required>
<div class="grid">
<div><label>Video format</label><select name="format"><option value="vertical">Vertical 9:16 (1080 × 1920)</option><option value="square">Square 1:1 (1080 × 1080)</option><option value="landscape">Landscape 16:9 (1920 × 1080)</option></select></div>
<div><label>Seconds per slide</label><input name="seconds_per_slide" type="number" min="1" max="30" value="5"></div>
</div>
<label>Heading (optional)</label><input name="heading" maxlength="100" placeholder="e.g. IELTS Academic Writing Task 1">
<label>Caption (optional)</label><textarea name="caption" rows="3" maxlength="220" placeholder="Short text displayed near the bottom of each slide"></textarea>
<label>Watermark</label><input name="watermark" maxlength="45" value="IELTS WINNERS">
<label>Narration text (optional; requires OPENAI_API_KEY)</label><textarea name="narration_text" rows="4" placeholder="Paste narration to generate speech"></textarea>
<label>Or upload narration audio (MP3, WAV, M4A, AAC or OGG)</label><input name="narration" type="file" accept=".mp3,.wav,.m4a,.aac,.ogg">
<small>Uploaded narration takes priority over generated narration. Generated narration uses the OpenAI API and is billed separately from ChatGPT.</small>
<button type="submit">Render MP4</button>
</form></main></body></html>""")


@app.post("/render")
async def render_video(
    slides: list[UploadFile] = File(...),
    format: str = Form("vertical"),
    seconds_per_slide: int = Form(5),
    heading: str = Form(""),
    caption: str = Form(""),
    watermark: str = Form("IELTS WINNERS"),
    narration_text: str = Form(""),
    narration: Optional[UploadFile] = File(None),
):
    if not slides or len(slides) > MAX_SLIDES:
        raise HTTPException(400, f"Upload between 1 and {MAX_SLIDES} slide images.")
    if seconds_per_slide < 1 or seconds_per_slide > 30:
        raise HTTPException(400, "Seconds per slide must be between 1 and 30.")
    dimensions = {
        "vertical": (1080, 1920),
        "square": (1080, 1080),
        "landscape": (1920, 1080),
    }
    if format not in dimensions:
        raise HTTPException(400, "Unsupported video format.")
    width, height = dimensions[format]
    job_id = uuid.uuid4().hex[:12]
    with tempfile.TemporaryDirectory(prefix="ielts-render-") as temp_name:
        temp = Path(temp_name)
        prepared = []
        total_bytes = 0
        for index, upload in enumerate(slides):
            suffix = Path(upload.filename or "").suffix.lower()
            if suffix not in ALLOWED_IMAGES:
                raise HTTPException(400, f"Unsupported slide file: {upload.filename}")
            raw = await upload.read()
            total_bytes += len(raw)
            if total_bytes > MAX_UPLOAD_BYTES:
                raise HTTPException(413, "Total slide upload size exceeds 40 MB.")
            source = temp / f"source_{index:03d}{suffix}"
            source.write_bytes(raw)
            output = temp / f"slide_{index:03d}.jpg"
            make_slide(source, output, width, height, heading, caption, watermark)
            prepared.append(output)

        concat_file = temp / "slides.txt"
        with concat_file.open("w", encoding="utf-8") as handle:
            for image_path in prepared:
                escaped = str(image_path).replace("'", "'\\''")
                handle.write(f"file '{escaped}'\n")
                handle.write(f"duration {seconds_per_slide}\n")
            escaped = str(prepared[-1]).replace("'", "'\\''")
            handle.write(f"file '{escaped}'\n")

        silent_video = temp / "silent.mp4"
        run_ffmpeg([
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-vf", "fps=30,format=yuv420p",
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            str(silent_video)
        ])

        audio_path = None
        if narration and narration.filename:
            audio_suffix = Path(narration.filename).suffix.lower()
            if audio_suffix not in ALLOWED_AUDIO:
                raise HTTPException(400, "Unsupported narration audio format.")
            audio_data = await narration.read()
            if len(audio_data) > MAX_UPLOAD_BYTES:
                raise HTTPException(413, "Narration audio exceeds 40 MB.")
            audio_path = temp / f"narration{audio_suffix}"
            audio_path.write_bytes(audio_data)
        elif narration_text.strip():
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise HTTPException(400, "Set OPENAI_API_KEY on the server or upload narration audio.")
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                speech = client.audio.speech.create(
                    model="gpt-4o-mini-tts",
                    voice="alloy",
                    input=narration_text.strip()[:4000],
                    response_format="mp3",
                )
                audio_path = temp / "narration.mp3"
                speech.stream_to_file(audio_path)
            except Exception as exc:
                raise HTTPException(502, f"Narration generation failed: {str(exc)[:500]}") from exc

        final_path = OUTPUT_DIR / f"ielts-video-{job_id}.mp4"
        if audio_path:
            run_ffmpeg([
                "-i", str(silent_video), "-i", str(audio_path),
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-shortest", "-movflags", "+faststart", str(final_path)
            ])
        else:
            shutil.copy2(silent_video, final_path)

    return FileResponse(
        final_path,
        media_type="video/mp4",
        filename=final_path.name,
        headers={"Content-Disposition": f'attachment; filename="{final_path.name}"'}
    )


@app.get("/download/{filename}")
def download_video(filename: str):
    if not re.fullmatch(r"ielts-video-[a-f0-9]{12}\.mp4", filename):
        raise HTTPException(404, "Video not found.")
    path = OUTPUT_DIR / filename
    if not path.is_file():
        raise HTTPException(404, "Video not found or expired.")
    return FileResponse(path, media_type="video/mp4", filename=filename)
