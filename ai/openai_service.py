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

        run = OpenaiService.execute_run(assistant_id, business_phone, client, instance_name, thread_id, user_phone)
        usage = run.usage
        if usage:
            from services.core.usage_tracker_service import UsageTrackerService
            UsageTrackerService.update_token_usage(
                establishment_id=business_phone,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens
            )

        messages = client.beta.threads.messages.list(thread_id=thread_id)
        for msg in messages.data:
            if msg.role == "assistant":
                final_response = msg.content[0].text.value
                logger.info(f"[AI] Resposta gerada: {final_response}")
                return final_response
        return ""

    @staticmethod
    def execute_run(assistant_id, business_phone, client, instance_name, thread_id, user_phone):
        run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant_id)
        count = 0
        while run.status not in ["completed", "failed", "cancelled"]:
            logger.info(f"[run.status] {run.status}")
            time.sleep(1)
            if count == 60:
                logger.warning(f"[Run Timeout] Tempo limite de execução atingido, cancelando a execução.")
                client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run.id)
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            if run.status == "requires_action":
                result = []
                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                for tool_call in tool_calls:
                    result.append(ToolHandler.resolve_and_submit_tool(business_phone, client, user_phone, instance_name,
                                                                      tool_call,
                                                                      thread_id, run.id))
                client.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread_id,
                    run_id=run.id,
                    tool_outputs=result
                )
            count += 1
        if run.status in ["failed", "cancelled"]:
            logger.warning(f"[AI] Run falhou ou foi cancelada.")
            run = OpenaiService.execute_run(assistant_id, business_phone, client, instance_name, thread_id, user_phone)
        return run
