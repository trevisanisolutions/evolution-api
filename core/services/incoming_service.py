import logging
import time

from soupsieve.util import lower

from core.controllers.dto.message_upsert_dto import MessageUpsertDTO
from core.dao.firebase_client import FirebaseClient
from core.services.buffer.buffer_service import BufferService
from core.services.conversation_history_service import ConversationHistoryService
from core.services.human_attendance_service import HumanAttendanceService
from core.services.whatsapp_service import WhatsappService
from core.utils.constants import MAX_MESSAGE_LENGTH

logger = logging.getLogger(__name__)


class IncomingService:

    @staticmethod
    def handle_incoming_message(incoming: MessageUpsertDTO):
        logger.debug(f"[handle_incoming_message]: Incoming{incoming}")
        logger.info(
            f"[IncomingService]-[Message Incoming]: Instance: {incoming.instance_name} | From: {incoming.user_identification} -> {incoming.user_msg}")
        if not incoming.user_msg:
            logger.warning(f"[handle_evolution_whatsapp] Empty message from {incoming.user_identification}")
            return None
        elif len(incoming.user_msg) > MAX_MESSAGE_LENGTH:
            return IncomingService._handle_message_max_length(incoming)
        elif "reset" == lower(incoming.user_msg):
            return IncomingService._handle_reset_context(incoming)
        elif incoming.from_me:
            if not incoming.is_admin:
                return IncomingService._handle_attendant_message(incoming.instance_name, incoming.business_phone,
                                                                 incoming.user_msg,
                                                                 incoming.user_phone)
            return BufferService.add_to_buffer(incoming.business_phone, incoming.user_phone, incoming.user_msg,
                                               incoming.instance_name)

        elif HumanAttendanceService.is_human_attendance_active(incoming.instance_name, incoming.business_phone,
                                                               incoming.user_phone):
            return ConversationHistoryService.append_message(incoming.business_phone, incoming.user_phone, "user",
                                                             incoming.user_msg)
        else:
            WhatsappService.mark_message_as_read(incoming.instance_name, incoming.remote_jid, incoming.message_id)
            BufferService.add_to_buffer(incoming.business_phone, incoming.user_phone, incoming.user_msg,
                                        incoming.instance_name)
            return ConversationHistoryService.append_message(incoming.business_phone, incoming.user_phone, "user",
                                                             incoming.user_msg)

    @staticmethod
    def _handle_reset_context(incoming):
        FirebaseClient.delete_data(f"establishments/{incoming.business_phone}/users/{incoming.user_phone}")
        FirebaseClient.delete_data(f"message_buffers/{incoming.user_phone}")
        logger.warning(f"Context has been reset: {incoming.user_identification}")
        WhatsappService.send_evolution_response(incoming.instance_name, incoming.user_phone,
                                                "Contexto resetado com sucesso.")

    @staticmethod
    def _handle_message_max_length(incoming):
        logger.warning(
            f"[handle_evolution_whatsapp] Message too long ({len(incoming.user_msg)}) -> {incoming.user_identification}: {incoming.user_msg}")
        user_resp = (
            "Opa! Sua mensagem é muito longa para processarmos de uma vez. "
            "Por favor, divida sua mensagem em partes menores ou seja mais específico. "
            "Isso nos ajuda a atendê-lo melhor e mais rapidamente."
        )
        WhatsappService.send_evolution_response(incoming.instance_name, incoming.user_phone, user_resp)

    @staticmethod
    def _handle_attendant_message(instance_name: str, business_phone: str, user_msg: str, user_phone: str):
        logger.debug(f"[handle_attendant_message] {instance_name} -> {business_phone} -> {user_phone} -> {user_msg}")
        now = int(time.time())
        FirebaseClient.save_data(
            f"establishments/{business_phone}/users/{user_phone}/human_attendance/last_message_timestamp", now)
        if "🤖" in user_msg.strip():
            human_attendance_path = f"establishments/{business_phone}/users/{user_phone}/human_attendance/active"
            human_attendance_flag = FirebaseClient.fetch_data(human_attendance_path) or False
            activated_message = "desativada" if human_attendance_flag else "reativada"
            message = f"🤖 IA {activated_message} manualmente."
            logger.warning(f"[handle_attendant_message] {message} para {user_phone} em {business_phone}")
            WhatsappService.send_evolution_response(instance_name, user_phone, message)
            FirebaseClient.save_data(human_attendance_path, not human_attendance_flag)
            ConversationHistoryService.append_message(business_phone, user_phone, "assistant", message)
        ConversationHistoryService.append_message(business_phone, user_phone, "[Atendente Humano]", user_msg)
