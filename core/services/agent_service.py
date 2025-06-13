import hashlib
import logging
import time

from openai import OpenAI
from openai.types.beta import Assistant

from core.dao.firebase_client import FirebaseClient
from core.utils.constants import AGENT_LAST_USED_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


class AgentService:
    @staticmethod
    def get_agent_config(business_phone: str, agent_id: str) -> dict:
        path = f"establishments/{business_phone}/agents/{agent_id}"
        return FirebaseClient.fetch_data(path)

    @staticmethod
    def get_assistant_id(business_phone: str, agent_id: str) -> str:
        config = AgentService.get_agent_config(business_phone, agent_id)
        return config.get("assistant_id") if config else None

    @staticmethod
    def get_assistant_by_id(business_phone: str, agent_id: str) -> Assistant:
        openai_key = FirebaseClient.fetch_data(f"establishments/{business_phone}/openai_key")
        assistant_id = AgentService.get_assistant_id(business_phone, agent_id)
        client = OpenAI(api_key=openai_key)
        assistant = client.beta.assistants.retrieve(assistant_id=assistant_id)
        return assistant

    @staticmethod
    def get_assistant_hash_instructions(business_phone: str, agent_id: str) -> str:
        assistant_instructions = AgentService.get_assistant_by_id(business_phone, agent_id).instructions
        hash_prompt = AgentService._hash_prompt(assistant_instructions)
        return hash_prompt

    @staticmethod
    def _hash_prompt(text: str) -> str:
        return hashlib.md5(text.strip().encode("utf-8")).hexdigest() if text else ""

    @staticmethod
    def get_agent_id(business_phone, user_phone):
        if business_phone == user_phone:
            has_admin = FirebaseClient.fetch_data(f"establishments/{business_phone}/agents/adm_agent")
            return "adm_agent" if has_admin else None
        current_agent = FirebaseClient.fetch_data(
            f"establishments/{business_phone}/users/{user_phone}/current_agent")
        if current_agent:
            current_agent_data = FirebaseClient.fetch_data(
                f"establishments/{business_phone}/users/{user_phone}/threads/{current_agent}")
            agent_last_used_at = current_agent_data.get("agent_last_used_at", 0)
            if current_agent and agent_last_used_at and (
                    int(time.time()) - agent_last_used_at < AGENT_LAST_USED_TIMEOUT_SECONDS):
                return current_agent
            else:
                logger.warning(
                    f"[get_agent_id] Timeout utilização de agente {current_agent} para {business_phone}/{user_phone}, ecaminhando para main_agent")
                return "main_agent"
        else:
            return "main_agent"
