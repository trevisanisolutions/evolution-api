# services/conversation_history_service.py
import inspect
import logging
import os
from typing import List, Dict

from openai import OpenAI

from dao.firebase_client import FirebaseClient
from services.core.agent_service import AgentService

HISTORY_LIMIT = 50

logger = logging.getLogger(__name__)


class ConversationHistoryService:

    @staticmethod
    def append_message(business_phone: str, user_phone: str, role: str, content: str, agent_id: str = None) -> None:
        stack = inspect.stack()
        caller_frame = stack[1]

        filename = os.path.splitext(os.path.basename(caller_frame.filename))[0]
        logger.info(
            f"[append_message] {business_phone}-> {user_phone} -> {role} -> {content} -> {agent_id} -> Arquivo:{filename} -> Função:{caller_frame.function} -> Linha:{caller_frame.lineno}")
        path = f"establishments/{business_phone}/users/{user_phone}/conversations"
        history: List[Dict] = FirebaseClient.fetch_data(path) or []

        display_role = ConversationHistoryService._get_display_role(business_phone, role, agent_id)
        history.append({"role": display_role, "content": content})
        if len(history) > HISTORY_LIMIT:
            history = history[-HISTORY_LIMIT:]

        FirebaseClient.save_data(path, history)

    @staticmethod
    def _get_display_role(business_phone: str, role: str, agent_id: str = None) -> str:
        if role == "user":
            return "[Usuário]"

        if role == "assistant":
            if agent_id:
                config = AgentService.get_agent_config(business_phone, agent_id)
                if config:
                    assistant_id = config.get("assistant_id")
                    if assistant_id:
                        openai_key = FirebaseClient.fetch_data(f"establishments/{business_phone}/openai_key")
                        client = OpenAI(api_key=openai_key)
                        assistant_info = client.beta.assistants.retrieve(assistant_id=assistant_id)
                        if assistant_info and assistant_info.name:
                            return f"[{assistant_info.name}]"
            return "[Agente]"

        return role
