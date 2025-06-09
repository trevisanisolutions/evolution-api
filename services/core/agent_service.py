# services/agent_service.py
import hashlib

from openai import OpenAI
from openai.types.beta import Assistant

from dao.firebase_client import FirebaseClient


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
