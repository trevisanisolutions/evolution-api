# services/buffer_service.py
import logging
import time

from dao.firebase_client import FirebaseClient
from utils.config import REPLICA_ID

logger = logging.getLogger(__name__)


class BufferService:

    @staticmethod
    def add_to_buffer(business_phone: str, user_phone: str, message: str, instance_name: str):
        path = f"message_buffers/{user_phone}"
        data = FirebaseClient.fetch_data(path) or {}
        now = int(time.time())

        # Inicializa se necessário
        messages = data.get("messages", [])
        messages.append(message)

        updates = {
            "establishment_phone": business_phone,
            "messages": messages,
            "last_updated": now,
            "presence": "available",
            "presence_last_updated": now
        }

        if "instance_name" not in data or not data.get("instance_name"):  # TODO: veriricar a necessidade desse campo
            updates["instance_name"] = instance_name
        if "replica_id" not in data or not data.get("replica_id"):
            updates["replica_id"] = REPLICA_ID
            updates["replica_id_last_updated"] = now

        FirebaseClient.update_data(path, updates)

    @staticmethod
    def update_presence(user_phone: str, presence: str, instance_name: str):
        logger.info(f"[update_presence] {user_phone} -> {presence}")
        path = f"message_buffers/{user_phone}"
        data = FirebaseClient.fetch_data(path) or {}

        updates = {
            # TODO: Verificar necessidade de gravar o establishment_phone neste momento (Talvez não precise )
            "presence": presence,
            "presence_last_updated": int(time.time())
        }

        if "instance_name" not in data or not data.get(
                "instance_name"):  # TODO: Verificar se o if precisa dessas duas verificações ou só a verificação simples já resolve
            updates["instance_name"] = instance_name
        if "replica_id" not in data or not data.get("replica_id"):
            updates["replica_id"] = REPLICA_ID
            updates["replica_id_last_updated"] = int(time.time())
        FirebaseClient.update_data(path, updates)

    @staticmethod
    def clear_buffer(user_phone: str):
        logger.info(f"[clear_buffer] {user_phone}")
        FirebaseClient.delete_data(f"message_buffers/{user_phone}")

    @staticmethod
    def get_all_buffers():
        logger.info("[get_all_buffers]")
        return FirebaseClient.fetch_data("message_buffers") or {}

    @staticmethod
    def update_buffer(user_phone: str, updates: dict):
        path = f"message_buffers/{user_phone}"
        FirebaseClient.update_data(path, updates)
