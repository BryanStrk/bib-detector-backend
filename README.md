---
title: Bib Detector API
emoji: 🏃
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

# Bib Detector API

A FastAPI backend that detects athlete **bib numbers** in race/sports photos and
returns each number with its bounding box and confidence. It pairs with a
separate React frontend.

## Endpoints

- `GET /health` — liveness probe; reports the active detection backend.
- `POST /detect` — upload a JPEG or PNG race photo, get back detected bib
  numbers (`bib_number`, `confidence`, `bbox` as `[x, y, w, h]`) plus the
  server-side `processing_time`.

## Detection pipeline

The pipeline is pluggable and chosen via config:

- **EasyOCR only (default MVP):** OCR runs on the whole image; numeric results
  of 1–5 digits become detections.
- **YOLO + EasyOCR (optional):** set `MODEL_PATH` to a YOLO `.pt` model to
  detect bib regions, crop each, and OCR the crop.

Both paths return the same schema, so the model can be swapped with no API
change. Detections below `MIN_CONFIDENCE` are filtered out.

## Configuration

Set via environment variables (Space **Settings → Variables and secrets**):

| Variable         | Description                                        | Default                                                    |
| ---------------- | -------------------------------------------------- | ---------------------------------------------------------- |
| `MODEL_PATH`     | Optional path to a YOLO `.pt` model.               | _(unset → EasyOCR MVP)_                                    |
| `CORS_ORIGINS`   | Comma-separated allowed frontend origins.          | `http://localhost:5173,https://bib-detector.example.com`   |
| `MIN_CONFIDENCE` | Discard detections below this confidence (0.0–1.0).| `0.3`                                                      |

## Deployment (Hugging Face Spaces, Docker SDK)

This repo is Space-ready. The container runs:

```
uvicorn app.main:app --host 0.0.0.0 --port 7860
```

EasyOCR model weights download to `/tmp/.EasyOCR` and all library caches are
pointed at `/tmp`, since HF Spaces only allow writes there.

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload          # http://127.0.0.1:8000/docs

# or with Docker, mirroring the Space:
docker build -t bib-detector .
docker run -p 7860:7860 bib-detector   # http://127.0.0.1:7860/docs
```
