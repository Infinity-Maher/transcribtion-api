# Transcription API

A FastAPI backend that accepts Arabic audio files, transcribes them using **Google Cloud Speech-to-Text**, then classifies the request into a service category using **Vertex AI Gemini**.

## How It Works

1. **Upload** an audio file (LINEAR16, 16 kHz) to `POST /upload-audio`
2. **Speech-to-Text** — Google Cloud STT transcribes the Arabic audio
3. **AI Classification** — Gemini analyzes the transcript and returns:
   - `cleaned_text` — grammatically corrected transcript
   - `category` — one of: نجارة (Carpentry), كهرباء (Electricity), سباكة (Plumbing), أعمال يدوية (Handicrafts)

## Tech Stack

- **FastAPI** — web framework
- **Google Cloud Speech-to-Text** — audio transcription
- **Vertex AI (Gemini)** — text classification
- **Docker** — containerized deployment
- **Google Cloud Run** — serverless hosting via GitHub Actions CI/CD

## Getting Started

### Prerequisites

- Python 3.11+
- A Google Cloud project with Speech-to-Text & Vertex AI APIs enabled
- Service account credentials

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `/docs`.

### Docker

```bash
docker build -t transcription-api .
docker run -p 8080:8080 transcription-api
```

## API

### `POST /upload-audio`

Upload an audio file for transcription and classification.

**Request:** `multipart/form-data` with a `file` field

**Response:**

```json
{
  "cleaned_text": "أريد إصلاح باب خشبي",
  "category": "نجارة"
}
```

## Deployment

Pushes to `main` automatically deploy to **Google Cloud Run** via GitHub Actions. The workflow requires a `GCP_CREDENTIALS` secret containing the service account JSON key.
