# dtos/whatsapp_webhook_dto.py
from utils.audio_transcriber import transcribe_audio_from_base64


class MessageUpsertDTO:
    def __init__(self, payload: dict):
        self.data = payload.get("data", {})
        self.key = self.data.get("key", {})
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

    def _extract_message(self):
        ignored_type = {
            "imageMessage", "videoMessage", "documentMessage",
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
            return transcribe_audio_from_base64(self.business_phone, audio_base64)
        return f"[{self.message_type} message]"
