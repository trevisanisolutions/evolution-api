import logging

from openai import OpenAI

from dao.firebase_client import FirebaseClient
from utils.date_utils import get_today_formated

logger = logging.getLogger(__name__)


class ThreadService:

    @staticmethod
    def get_thread_id(business_phone: str, user_phone: str, agent_id: str) -> str:
        logger.info(f"[get_thread_id] {user_phone} -> {agent_id}")
        path = f"establishments/{business_phone}/users/{user_phone}/threads/{agent_id}"
        thread_info = FirebaseClient.fetch_data(path) or {}
        if thread_info:
            logger.info(
                f"[get_thread_id] Reutilização thread: {thread_info.get('thread_id')} para {business_phone}/{user_phone}/{agent_id}")
            return thread_info.get("thread_id")
        else:
            return ThreadService.create_new_thread(business_phone, agent_id, path, user_phone)

    @staticmethod
    def create_new_thread(business_phone, agent_id, path, user_phone):
        openai_key = FirebaseClient.fetch_data(f"establishments/{business_phone}/openai_key")
        client = OpenAI(api_key=openai_key)
        thread = client.beta.threads.create()
        thread_info = {"thread_id": thread.id}
        context = f"⚠️ CONTEXTO AUXILIAR: Hoje é {get_today_formated()}"
        logger.info(f"[create_new_thread] Envio de contexto auxiliar: {context}")
        client.beta.threads.messages.create(thread_id=thread.id, role="user", content=context)
        FirebaseClient.save_data(path, thread_info)
        logger.info(
            f"[create_new_thread] Nova thread criada: {thread_info.get('thread_id')} para {user_phone}/{agent_id}")
        return thread_info.get("thread_id")
