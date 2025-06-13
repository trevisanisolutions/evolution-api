import logging
import time

from openai import OpenAI

from core.dao.firebase_client import FirebaseClient
from core.services.agent_service import AgentService
from core.utils.constants import REUSE_THREAD_LAST_USED_TIMEOUT

logger = logging.getLogger(__name__)


class ThreadService:

    @staticmethod
    def get_thread_id(business_phone: str, user_phone: str, agent_id: str) -> str:
        logger.debug(f"[get_thread_id] {user_phone} -> {agent_id}")
        thread_path = f"establishments/{business_phone}/users/{user_phone}/threads/{agent_id}"
        assistant_hash_instructions = AgentService.get_assistant_hash_instructions(business_phone, agent_id)
        thread_info = FirebaseClient.fetch_data(thread_path) or {}
        current_time = int(time.time())
        thread_last_used_at = thread_info.get("thread_last_used_at", 0)

        if current_time - thread_last_used_at < REUSE_THREAD_LAST_USED_TIMEOUT and thread_info and thread_info.get(
                "hash_instructions",
                "") == assistant_hash_instructions:

            logger.info(
                f"[get_thread_id] Reutilização thread: {thread_info.get('thread_id')} para {business_phone}/{user_phone}/{agent_id}")
            FirebaseClient.update_data(thread_path, {
                "thread_last_used_at": current_time
            })
            return thread_info.get("thread_id")
        else:
            new_thread_id = ThreadService.create_new_thread(
                business_phone, agent_id, thread_path, user_phone, assistant_hash_instructions)
            return new_thread_id

    @staticmethod
    def create_new_thread(business_phone, agent_id, path, user_phone, assistant_hash_instructions) -> str:
        openai_key = FirebaseClient.fetch_data(f"establishments/{business_phone}/openai_key")
        client = OpenAI(api_key=openai_key)
        thread = client.beta.threads.create()
        current_time = int(time.time())
        thread_info = {"thread_id": thread.id, "hash_instructions": assistant_hash_instructions,
                       "thread_last_used_at": current_time}
        FirebaseClient.save_data(path, thread_info)
        logger.info(
            f"[create_new_thread] Nova thread criada: {thread_info.get('thread_id')} para {user_phone}/{agent_id}")
        return thread_info.get("thread_id")
