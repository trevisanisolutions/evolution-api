import logging
import time

from core.dao.firebase_client import FirebaseClient
from core.services.agent_service import AgentService
from core.services.conversation_history_service import ConversationHistoryService
from core.services.openai_service import OpenaiService

logger = logging.getLogger(__name__)


class ProcessMessageService:

    @staticmethod
    def process_user_message(business_phone: str, user_message: str, user_phone: str, instance_name: str):
        logger.debug(f"[process_message] {user_phone} -> {business_phone} -> {instance_name} -> {user_message}")
        agent_id = AgentService.get_agent_id(business_phone, user_phone)
        if not agent_id:
            is_admin = "Sim" if business_phone == user_phone else "Não"
            logger.warning(
                f"[process_message] Nenhum agente encontrado para {business_phone}/{user_phone} (ADM:{is_admin})")
            return "*_Sistema_*: Nenhum agente disponível no momento."
        else:
            FirebaseClient.update_data(
                f"establishments/{business_phone}/users/{user_phone}/threads/{agent_id}",
                {"agent_last_used_at": int(time.time())}
            )
        response = OpenaiService.get_ai_response(business_phone, user_message, user_phone, agent_id, instance_name)
        logger.debug(f"[AI Response] {user_phone} -> {instance_name} -> {response}")
        ConversationHistoryService.append_message(business_phone, user_phone, "assistant", response, agent_id)
        agent_config = AgentService.get_agent_config(business_phone, agent_id)
        return f"*_{agent_config.get('name')}_*: {response}"
