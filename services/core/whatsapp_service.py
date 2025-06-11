import logging
import os
import time

import requests

from ai.openai_service import OpenaiService
from controllers.dto.message_upsert_dto import MessageUpsertDTO
from dao.firebase_client import FirebaseClient
from services.core.agent_service import AgentService
from services.core.buffer.buffer_service import BufferService
from services.core.conversation_history_service import ConversationHistoryService
from utils.whatsapp_chat_utils import mark_message_as_read

logger = logging.getLogger(__name__)

HUMAN_ATTENDANCE_LAST_UPDATE_LIMIT = 900


class WhatsappService:

    @staticmethod
    def process_incoming_message(incoming: MessageUpsertDTO):
        logger.info(
            f"[process_incoming_message] {incoming.instance_name} -> {incoming.remote_jid} -> {incoming.user_msg}")
        logger.info(
            f"[incoming_message] {incoming.instance_name} -> {incoming.user_push_name} -> {incoming.user_msg}")
        if incoming.business_phone == incoming.user_phone:
            mark_message_as_read(incoming.instance_name, incoming.remote_jid, incoming.message_id)
            return BufferService.add_to_buffer(incoming.business_phone, incoming.user_phone, incoming.user_msg,
                                               incoming.instance_name)
        if incoming.from_me:
            return WhatsappService._handle_attendant_message(incoming.business_phone, incoming.user_msg,
                                                             incoming.user_phone)
        if WhatsappService._is_human_attendance_active(incoming.business_phone, incoming.user_phone):
            return ConversationHistoryService.append_message(incoming.business_phone, incoming.user_phone, "user",
                                                             incoming.user_msg)
        mark_message_as_read(incoming.instance_name, incoming.remote_jid, incoming.message_id)
        BufferService.add_to_buffer(incoming.business_phone, incoming.user_phone, incoming.user_msg,
                                    incoming.instance_name)
        return ConversationHistoryService.append_message(incoming.business_phone, incoming.user_phone, "user",
                                                         incoming.user_msg)

    @staticmethod
    def _handle_attendant_message(business_phone: str, user_msg: str, user_phone: str):
        now = int(time.time())
        FirebaseClient.save_data(
            f"establishments/{business_phone}/users/{user_phone}/human_attendance/last_message_timestamp", now)
        if "🤖" in user_msg.strip():
            FirebaseClient.save_data(f"establishments/{business_phone}/users/{user_phone}/human_attendance/active",
                                     False)
            ConversationHistoryService.append_message(business_phone, user_phone, "assistant",
                                                      "🤖 (IA reativada manualmente)")
        ConversationHistoryService.append_message(business_phone, user_phone, "[Atendente Humano]", user_msg)

    @staticmethod
    def process_user_message(business_phone: str, user_message: str, user_phone: str, instance_name: str):
        logger.info(f"[process_message] {user_phone} -> {business_phone} -> {instance_name} -> {user_message}")
        agent_id = WhatsappService.get_agent_id(business_phone, user_phone)
        if not agent_id:
            is_admin = "Sim" if business_phone == user_phone else "Não"
            logger.warning(
                f"[process_message] Nenhum agente encontrado para {business_phone}/{user_phone} (ADM:{is_admin})")
            return "*_Sistema_*: Nenhum agente disponível no momento."
        response = OpenaiService.get_ai_response(business_phone, user_message, user_phone, agent_id, instance_name)
        logger.info(f"[response] {user_phone} -> {instance_name} -> {response}")
        ConversationHistoryService.append_message(business_phone, user_phone, "assistant", response, agent_id)
        agent_config = AgentService.get_agent_config(business_phone, agent_id)
        return f"*_{agent_config.get('name')}_*: {response}"

    @staticmethod
    def get_agent_id(business_phone, user_phone):
        if business_phone == user_phone:
            if FirebaseClient.fetch_data(f"establishments/{business_phone}/agents/adm_agent"):
                return "adm_agent"
            else:
                return None
        return FirebaseClient.fetch_data(
            f"establishments/{business_phone}/users/{user_phone}/current_agent") or "main_agent"

    @staticmethod
    def send_evolution_response(instance_name, to_number, message_text):
        logger.info(
            f"[send_evolution_response] {to_number} -> {message_text}")
        try:
            api_key = os.environ.get('EVOLUTION_API_KEY')
            api_url = os.environ.get('EVOLUTION_API_URL')
            endpoint = f"{api_url}/message/sendText/{instance_name}"
            headers = {
                'apikey': api_key,
                'Content-Type': 'application/json'
            }
            to_number_formatted = to_number.split('@')[0] if '@' in to_number else to_number
            payload = {
                'number': to_number_formatted,
                'options': {'delay': 1200},
                'text': message_text
            }
            logger.info(f"[send_evolution_response] Enviando resposta para número formatado: {to_number_formatted}")
            response = requests.post(endpoint, json=payload, headers=headers)
            if response.status_code not in [200, 201]:
                logger.error(f"Erro ao enviar mensagem: {response.text}")
            return response.json() if response.text else {'status': response.status_code}
        except Exception as e:
            logger.error(f"Erro ao enviar resposta: {str(e)}")
            return None

    @staticmethod
    def _is_human_attendance_active(business_phone: str, user_phone: str) -> bool:
        now = int(time.time())
        attendance = FirebaseClient.fetch_data(
            f"establishments/{business_phone}/users/{user_phone}/human_attendance") or {}
        active = attendance.get("active", False)
        last_ts = attendance.get("last_message_timestamp", 0)

        if active and (now - last_ts > HUMAN_ATTENDANCE_LAST_UPDATE_LIMIT):
            FirebaseClient.save_data(f"establishments/{business_phone}/users/{user_phone}/human_attendance/active",
                                     False)
            return False

        return active
