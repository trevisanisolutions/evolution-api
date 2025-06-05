import logging
import time

from openai import OpenAI

from dao.firebase_client import FirebaseClient
from services.core.agent_service import AgentService
from services.core.thread_service import ThreadService
from services.core.tool_handler import ToolHandler

logger = logging.getLogger(__name__)


class OpenaiService:

    @staticmethod
    def get_ai_response(business_phone: str, user_msg: str, user_phone: str, agent_id: str, instance_name: str) -> str:
        logger.info(
            f"[get_ai_response] {user_phone} -> {user_msg} -> {agent_id}")
        thread_id = ThreadService.get_thread_id(business_phone, user_phone, agent_id)
        api_key = FirebaseClient.fetch_data(f"establishments/{business_phone}/openai_key")
        client = OpenAI(api_key=api_key)
        client.beta.threads.messages.create(thread_id=thread_id, role="user", content=user_msg)

        assistant_id = AgentService.get_assistant_id(business_phone, agent_id)

        run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant_id)

        while run.status not in ["completed", "failed", "cancelled"]:
            logger.info(f"[run.status] {run.status}")
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            if run.status == "requires_action":
                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                for tool_call in tool_calls:
                    ToolHandler.resolve_and_submit_tool(business_phone, client, user_phone, instance_name, tool_call,
                                                        thread_id, run.id)

        messages = client.beta.threads.messages.list(thread_id=thread_id)
        for msg in messages.data:
            if msg.role == "assistant":
                final_response = msg.content[0].text.value
                logger.info(f"[AI] Resposta gerada: {final_response}")
                return final_response
        return ""
