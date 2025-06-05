# services/agent_service.py

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
