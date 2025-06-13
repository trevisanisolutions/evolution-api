import logging
import time

from core.dao.firebase_client import FirebaseClient
from core.utils.constants import REPLICA_ID

logger = logging.getLogger(__name__)


class BufferService:

    @staticmethod
    def add_to_buffer(business_phone: str, user_phone: str, message: str, instance_name: str):
        logger.debug(f"[add_to_buffer] {instance_name} -> {user_phone} -> {message}")
        path = f"message_buffers/{user_phone}"
        data = FirebaseClient.fetch_data(path) or {}
        now = int(time.time())

        messages = data.get("messages", [])
        messages.append(message)

        updates = {
            "establishment_phone": business_phone,
            "messages": messages,
            "last_updated": now,
            "presence": "available",
            "presence_last_updated": now,
            "instance_name": instance_name
        }
        if "replica_id" not in data or not data.get("replica_id"):
            updates["replica_id"] = REPLICA_ID
            updates["replica_id_last_updated"] = now

        FirebaseClient.update_data(path, updates)

    @staticmethod
    def update_presence_to_buffer(user_phone: str, presence: str):
        logger.debug(f"[update_presence_to_buffer] {user_phone} -> {presence}")
        data = FirebaseClient.fetch_data(f"message_buffers/{user_phone}") or {}
        now = int(time.time())
        updates = {
            "presence": presence,
            "presence_last_updated": now
        }
        if "replica_id" not in data or not data.get("replica_id"):
            updates["replica_id"] = REPLICA_ID
            updates["replica_id_last_updated"] = now
        BufferService.update_buffer(user_phone, updates)

    @staticmethod
    def clear_buffer(user_phone: str):
        logger.debug(f"[clear_buffer] {user_phone}")
        FirebaseClient.delete_data(f"message_buffers/{user_phone}")

    @staticmethod
    def get_all_buffers():
        logger.debug("[get_all_buffers]")
        return FirebaseClient.fetch_data("message_buffers") or {}

    @staticmethod
    def update_buffer(user_phone: str, updates: dict):
        path = f"message_buffers/{user_phone}"
        FirebaseClient.update_data(path, updates)
