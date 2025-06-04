# utils/audio_transcriber.py
import base64
import os
import tempfile

from openai import OpenAI

from dao.firebase_client import FirebaseClient


def transcribe_audio_from_base64(business_phone: str, base64_data: str, extension=".ogg") -> str:
    try:
        openai_key = FirebaseClient.fetch_data(f"establishments/{business_phone}/openai_key")
        client = OpenAI(api_key=openai_key)  # ← move para dentro da função
        audio_bytes = base64.b64decode(base64_data)

        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        with open(temp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            return transcript.text.strip()

    except Exception as e:
        return f"[Erro na transcrição: {str(e)}]"

    finally:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
