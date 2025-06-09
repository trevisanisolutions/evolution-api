import logging

from openai import OpenAI

from dao.firebase_client import FirebaseClient
from services.core.agent_service import AgentService

logger = logging.getLogger(__name__)


class ThreadService:

    @staticmethod
    def get_thread_id(business_phone: str, user_phone: str, agent_id: str) -> str:
        logger.info(f"[get_thread_id] {user_phone} -> {agent_id}")
        path = f"establishments/{business_phone}/users/{user_phone}/threads/{agent_id}"
        assistant_hash_instructions = AgentService.get_assistant_hash_instructions(business_phone, agent_id)
        thread_info = FirebaseClient.fetch_data(path) or {}
        if thread_info and thread_info.get("hash_instructions", "") == assistant_hash_instructions:
            logger.info(
                f"[get_thread_id] Reutilização thread: {thread_info.get('thread_id')} para {business_phone}/{user_phone}/{agent_id}")
            return thread_info.get("thread_id")
        else:
            return ThreadService.create_new_thread(business_phone, agent_id, path, user_phone,
                                                   assistant_hash_instructions)

    @staticmethod
    def create_new_thread(business_phone, agent_id, path, user_phone, assistant_hash_instructions) -> str:
        openai_key = FirebaseClient.fetch_data(f"establishments/{business_phone}/openai_key")
        client = OpenAI(api_key=openai_key)
        thread = client.beta.threads.create()
        thread_info = {"thread_id": thread.id, "hash_instructions": assistant_hash_instructions}
        FirebaseClient.save_data(path, thread_info)
        logger.info(
            f"[create_new_thread] Nova thread criada: {thread_info.get('thread_id')} para {user_phone}/{agent_id}")
        return thread_info.get("thread_id")
