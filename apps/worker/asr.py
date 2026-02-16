import os
from openai import OpenAI
import json

def transcribe_audio(file_path: str, language_hint: str | None = None) -> list[dict]:
    """
    Transcribes audio file using OpenAI Whisper API.
    Returns list of segments: [{"start": 0.0, "end": 10.0, "text": "...", "lang": "en", "speaker": None, "confidence": 0.9}]
    """
    api_key = os.environ.get("ASR_API_KEY") or os.environ.get("LLM_API_KEY")
    if not api_key:
        raise RuntimeError("ASR_API_KEY or LLM_API_KEY is required for transcription.")

    client = OpenAI(api_key=api_key)

    with open(file_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",
            language=language_hint if language_hint else None
        )

    # Extract segments
    segments = []
    if hasattr(transcript, 'segments'):
        for s in transcript.segments:
            segments.append({
                "start": s.start,
                "end": s.end,
                "text": s.text.strip(),
                "lang": getattr(transcript, 'language', 'en'), # Whisper returns language at top level usually
                "speaker": None, # Whisper API doesn't do diarization by default usually
                "confidence": getattr(s, 'avg_logprob', None) # Proxy for confidence
            })
    else:
        # Fallback if no segments provided (unlikely with verbose_json)
        segments.append({
            "start": 0.0,
            "end": transcript.duration,
            "text": transcript.text,
            "lang": getattr(transcript, 'language', 'en'),
            "speaker": None,
            "confidence": 1.0
        })

    return segments
