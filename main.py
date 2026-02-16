from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
from google.cloud import speech
from google import genai
from google.genai import types
from pydub import AudioSegment
import json
import io
from enum import Enum

app = FastAPI(title="Audio Transcription & Reasoning API")

# --- 1. Initialize Clients ---
speech_client = speech.SpeechClient()
vertex_client = genai.Client(
    vertexai=True,
    project='gdghackathon-487512',
    location='global'
)

# --- 2. Output Schema ---


class ServiceCategory(str, Enum):
    carpentry = "نجارة"
    electricity = "كهرباء"
    plumbing = "سباكة"
    handicrafts = "نقاش"


class EnhancedTranscriptionSchema(BaseModel):
    cleaned_text: str = Field(
        description="The grammatically corrected transcript.")
    category: ServiceCategory = Field(
        description="The single service category that best matches the user's request.")


# --- 3. The Unified Endpoint ---

@app.post("/upload-audio")
async def process_audio(file: UploadFile = File(...)):
    # Step A: Read the audio file directly into memory (bytes)
    try:
        audio_bytes = await file.read()
    except Exception:
        raise HTTPException(
            status_code=400, detail="Could not read the uploaded file.")

    print(f"Processing {file.filename}...")

    # Step A2: Convert any audio format to WAV (LINEAR16, 16kHz, mono)
    try:
        audio_input = io.BytesIO(audio_bytes)
        # Determine format from file extension, fallback to ffmpeg auto-detect
        ext = file.filename.rsplit(
            ".", 1)[-1].lower() if file.filename and "." in file.filename else None
        if ext in ("wav", "mp3", "ogg", "flac", "aac", "m4a", "wma", "webm", "mp4"):
            audio_segment = AudioSegment.from_file(audio_input, format=ext)
        else:
            audio_segment = AudioSegment.from_file(audio_input)

        # Convert to mono, 16kHz, 16-bit PCM WAV
        audio_segment = audio_segment.set_channels(
            1).set_frame_rate(16000).set_sample_width(2)
        wav_buffer = io.BytesIO()
        audio_segment.export(wav_buffer, format="wav")
        wav_bytes = wav_buffer.getvalue()
        print(f"Converted to WAV: {len(wav_bytes)} bytes")
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Could not convert audio file: {str(e)}")

    # Step B: Pass the converted WAV bytes to Google Cloud Speech-to-Text
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="ar-EG",
    )
    audio = speech.RecognitionAudio(content=wav_bytes)

    try:
        stt_response = speech_client.recognize(config=config, audio=audio)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Speech-to-Text API Error: {str(e)}")

    if not stt_response.results:
        raise HTTPException(
            status_code=400, detail="No speech recognized in the audio.")

    raw_transcript = " ".join(
        [result.alternatives[0].transcript for result in stt_response.results])
    print(f"Raw Transcript extracted: {raw_transcript}")

    # Step C: Pass the raw transcript to Vertex AI Gemini for classification
    instruction = """
        أنت مساعد ذكي ضمن منصة إلكترونية تربط العملاء بمقدمي خدمات الحرف اليدوية والصيانة المنزلية.
        مهمتك هي تحليل النص المستخرج من الكلام (Speech-to-Text) وتصنيفه إلى فئة واحدة فقط من الفئات التالية:

        الفئات المتاحة:
        - "نجارة": أي شيء يتعلق بالخشب، الأثاث، الأبواب، النوافذ، الأرفف، الدواليب، أو أعمال النجارة.
        - "كهرباء": أي شيء يتعلق بالأسلاك، المفاتيح، الإضاءة، الأعطال الكهربائية، التوصيلات، أو الأجهزة الكهربائية.
        - "سباكة": أي شيء يتعلق بالمياه، المواسير، الحنفيات، الصرف، التسريب، الحمامات، أو المطابخ من ناحية المياه.
        - "أعمال يدوية": أي شيء يتعلق بالحرف اليدوية، التطريز، الخياطة، الفخار، النسيج، الجلود، الزجاج، الدهان، السيراميك، أو أي خدمة لا تنتمي للفئات الثلاث الأخرى.

        القواعد:
        1. اختر فئة واحدة فقط من الأربع فئات المذكورة أعلاه.
        2. إذا كان النص غير واضح أو لا ينتمي بوضوح لأي فئة، اختر "أعمال يدوية".
        3. أعد نسخة نظيفة ومصححة نحوياً من النص الأصلي.
        4. أعد JSON فقط بدون أي شرح إضافي.
    """
    try:
        gemini_response = vertex_client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=raw_transcript,
            config=types.GenerateContentConfig(
                system_instruction=instruction,
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=EnhancedTranscriptionSchema,
            )
        )
        return json.loads(gemini_response.text)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Vertex AI Error: {str(e)}")
