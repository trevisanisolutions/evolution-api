import base64
import os
import tempfile

from openai import OpenAI

from core.dao.firebase_client import FirebaseClient


def _transcribe_audio_from_base64(business_phone: str, base64_data: str, extension=".ogg") -> str:
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


class MessageUpsertDTO:
    def __init__(self, payload: dict):
        self.data = payload.get("data")
        if self.data is None:
            raise ValueError("Payload data is missing or invalid")
        self.key = self.data.get("key")
        if self.key is None:
            raise ValueError("Payload key is missing or invalid")
        self.message_data = self.data.get("message", {})
        self.message_type = self.data.get("messageType", "")
        self.remote_jid = self.key.get("remoteJid", "")
        self.user_phone = self.remote_jid.split("@")[0]
        self.message_id = self.key.get("id")
        self.from_me = self.key.get("fromMe", False)
        self.instance_name = payload.get("instance", "")
        self.sender = payload.get("sender", "")
        self.business_phone = self.sender.split("@")[0]
        self.user_msg = self._extract_message()
        self.user_push_name = self.data.get("pushName", "Desconhecido")
        self.is_admin = self.business_phone == self.user_phone
        self.user_identification = f"{self.user_push_name}-({self.user_phone})"
        self.user_phone_area_code = self.user_phone[2:4] if len(self.user_phone) >= 4 else ""

    def _extract_message(self):
        ignored_type = {
            "imageMessage", "videoMessage", "documentMessage", "videoMessage",
            "stickerMessage", "reactionMessage", "locationMessage", "liveLocationMessage", "ptvMessage"
        }
        if self.message_type in ignored_type:
            return None
        if self.message_type == "conversation":
            return self.message_data.get("conversation", "").strip()
        elif self.message_type == "extendedTextMessage":
            return self.message_data.get("extendedTextMessage", {}).get("text", "").strip()
        elif self.message_type in {"audio", "voice", "ptt", "audioMessage"}:
            audio_base64 = self.message_data.get("base64", "")
            return _transcribe_audio_from_base64(self.business_phone, audio_base64)
        return f"[{self.message_type} message]"

    def __str__(self):
        return (
            f"MessageUpsertDTO("
            f"user_phone={self.user_phone}, "
            f"user_push_name={self.user_push_name}, "
            f"message_type={self.message_type}, "
            f"user_msg={self.user_msg}, "
            f"instance_name={self.instance_name}, "
            f"business_phone={self.business_phone}"
            f")"
        )
