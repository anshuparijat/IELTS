# IELTS AI Video Renderer

A private-workflow foundation for producing vertical 9:16 teaching videos from uploaded slides, narration, and visual instructions.

## Planned workflow

1. Upload slide images and narration (or provide narration text).
2. Configure video size, slide timing, captions, and visual annotations.
3. Render an MP4 using FFmpeg.
4. Return a downloadable MP4 from the renderer interface.

## Architecture

- **FastAPI**: upload and render interface/API.
- **FFmpeg**: video assembly and encoding.
- **Pillow**: image preparation and text overlays.
- **OpenAI API (optional)**: text-to-speech when an API key is configured.
- **Render**: hosts the web renderer.
- **GitHub**: source control and deployment workflow.

## Current status

This repository is the application foundation. The next implementation milestone is the upload/render interface and MP4 download endpoint.

## Local development

Requires Python 3.11+ and FFmpeg.

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Open http://127.0.0.1:8000.

## Environment variables

- `OPENAI_API_KEY` (optional): enables generated narration through the OpenAI API. A ChatGPT subscription does not include API credits.
- `OUTPUT_DIR` (optional): output directory; defaults to `outputs`.

## Deployment

A `render.yaml` blueprint is included. Configure the optional `OPENAI_API_KEY` as a secret in the hosting provider dashboard. Do not commit API keys, passwords, or tokens.

## Important download behaviour

The renderer's web interface will expose a direct MP4 download endpoint. A GitHub Actions artifact is a separate download mechanism; it does not automatically become an attachment in a ChatGPT conversation.
