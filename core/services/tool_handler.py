import json
import logging
import time

from openai.types.beta.threads import RequiredActionFunctionToolCall

from clients.sec24.registration.registration_service import SEC24UserService
from core.dao.firebase_client import FirebaseClient
from core.services.agent_service import AgentService
from core.services.buffer.buffer_service import BufferService
from core.services.calendar.calendar_functions import get_appointments, check_availabilities, reschedule_appointments, \
    cancel_appointments, \
    create_appointments
from core.services.thread_service import ThreadService

logger = logging.getLogger(__name__)


class ToolHandler:

    @staticmethod
    def resolve_and_submit_tool(business_phone: str, user_phone: str, instance_name: str,
                                tool_call: RequiredActionFunctionToolCall):
        tool_name = tool_call.function.name
        logger.debug(f"[resolve_and_submit_tool] {tool_name} -> {business_phone} -> {user_phone}")

        try:
            args = json.loads(tool_call.function.arguments) if isinstance(tool_call.function.arguments,
                                                                          str) else tool_call.function.arguments
            logger.debug(f"[resolve_and_submit_tool] {tool_name} -> {args}")
            match tool_name:
                case "criar_agendamentos":
                    result = create_appointments(args)

                case "cancelar_agendamentos":
                    result = cancel_appointments(args, business_phone == user_phone)

                case "reagendar_agendamentos":
                    result = reschedule_appointments(args, business_phone == user_phone)

                case "verificar_disponibilidades":
                    result = check_availabilities(args)

                case "verificar_agendamentos":
                    result = get_appointments(args)

                case "registrar_usuario":
                    result = SEC24UserService.register_user(args)

                case "verificar_cadastro":
                    result = SEC24UserService.check_registration(args)

                case "trocar_agente":
                    result = ToolHandler._handle_switch_agent(args, business_phone, user_phone, instance_name)

                case "atendimento_humano":
                    result = ToolHandler._handle_human_attendance(business_phone, user_phone)

                case _:
                    result = {"message": f"Tool '{tool_name}' not supported."}
            logger.debug(f"[toll_response]: {instance_name} -> {user_phone} -> {result}")
            return {"tool_call_id": tool_call.id, "output": json.dumps(result)}


        except Exception as e:
            logger.error(f"Erro ao executar tool '{tool_name}': {str(e)}")
            return {"tool_call_id": tool_call.id,
                    "output": ToolHandler._build_error_response("Erro ao executar a função")}

    @staticmethod
    def _handle_switch_agent(args, business_phone, user_phone, instance_name):
        new_agent_id = args.get("agent_id")
        logger.debug(f"[_handle_switch_agent] {args} -> {business_phone} -> {user_phone}")
        if not new_agent_id:
            return ToolHandler._build_error_response(f"Parâmetro 'agent_id' ausente.")
        agent_info = FirebaseClient.fetch_data(f"establishments/{business_phone}/agents/{new_agent_id}")
        if not agent_info:
            return ToolHandler._build_error_response(f"Agente {new_agent_id} não disponível")
        context_summary = args.get("context_summary")
        if not context_summary:
            return ToolHandler._build_error_response(f"Parâmetro 'context_summary' ausente.")
        path = f"establishments/{business_phone}/users/{user_phone}/threads/{new_agent_id}"
        assistant_hash_instructions = AgentService.get_assistant_hash_instructions(business_phone, new_agent_id)
        ThreadService.create_new_thread(business_phone, new_agent_id, path, user_phone, assistant_hash_instructions)
        BufferService.add_to_buffer(business_phone, user_phone, f"⚠️ CONTEXTO AUTOMÁTICO: {context_summary}",
                                    instance_name)
        BufferService.add_to_buffer(business_phone, user_phone, "Olá", instance_name)
        FirebaseClient.save_data(f"establishments/{business_phone}/users/{user_phone}/current_agent", new_agent_id)
        return ToolHandler._build_success_response("Troca de agente concluída com sucesso")

    @staticmethod
    def _handle_human_attendance(business_phone, user_phone):
        FirebaseClient.save_data(f"establishments/{business_phone}/users/{user_phone}/human_attendance/active", True)
        FirebaseClient.save_data(
            f"establishments/{business_phone}/users/{user_phone}/human_attendance/last_message_timestamp",
            int(time.time()))
        logger.info(f"Atendimento humano iniciado para {user_phone} em {business_phone}")
        return ToolHandler._build_success_response("Atendimento humano iniciado com sucesso")

    @staticmethod
    def _build_success_response(message: str):
        logger.debug(f"[_build_success_response] {message} ")
        return {"status": "success", "message": message}

    @staticmethod
    def _build_error_response(message: str):
        logger.warning(f"[_build_error_response] {message} ")
        return {"status": "error", "message": message}
