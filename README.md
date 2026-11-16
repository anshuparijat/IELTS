# IELTS AI Video Renderer

A GitHub-based teaching-video renderer for slide images and spoken narration.

## Voice

Narration uses Microsoft Edge text-to-speech voice **Andrew (US)**, voice ID `en-US-AndrewNeural`. No OpenAI API key is required for this voice. It uses the Edge TTS service over the network.

## Render through GitHub Actions

1. Add slide images to `assets/slides/` in the order you want them shown. Use filenames such as `01-intro.png`, `02-chart.png`, `03-summary.png`.
2. Open the repository's **Actions** tab.
3. Select **Render teaching video**.
4. Choose **Run workflow**.
5. Enter the narration, slide folder, seconds per slide and watermark.
6. When the workflow finishes, open the run and download the `ielts-video-mp4` artifact.

The GitHub Actions renderer outputs a vertical 9:16 MP4 (1080 × 1920) with Andrew US narration.

## Web renderer

The FastAPI application in `app.py` also supports slide uploads, uploaded narration audio, generated Andrew US narration, and an MP4 download response.

## Local development

Requires Python 3.11+ and FFmpeg.

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Open http://127.0.0.1:8000.

## Output and delivery

GitHub Actions stores each completed MP4 as a downloadable workflow artifact for 7 days. This is a GitHub download, not an automatic ChatGPT conversation attachment. Direct attachment delivery into ChatGPT requires a separate supported file-transfer integration.
