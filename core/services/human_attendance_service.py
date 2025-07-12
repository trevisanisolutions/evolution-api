import logging
import time

from core.dao.firebase_client import FirebaseClient
from core.services.conversation_history_service import ConversationHistoryService
from core.services.whatsapp_service import WhatsappService
from core.utils.constants import HUMAN_ATTENDANT_LAST_UPDATE_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


class HumanAttendanceService:

    @staticmethod
    def is_human_attendance_active(instance_name: str, business_phone: str, user_phone: str) -> bool:
        now = int(time.time())
        attendance = FirebaseClient.fetch_data(
            f"establishments/{business_phone}/users/{user_phone}/human_attendance") or {}
        active = attendance.get("active", False)
        last_ts = attendance.get("last_message_timestamp", 0)

        if active and (now - last_ts > HUMAN_ATTENDANT_LAST_UPDATE_TIMEOUT_SECONDS):
            FirebaseClient.save_data(f"establishments/{business_phone}/users/{user_phone}/human_attendance/active",
                                     False)
            message = "Atendimento humano desativado por inatividade do atendente. Aguarde um momento..."
            logger.warning(
                f"[is_human_attendance_active] {instance_name} -> Atendimento humano desativado para {user_phone} por inatividade.")
            WhatsappService.send_evolution_response(instance_name, user_phone, message)
            return False

        return active

    @staticmethod
    def is_ia_disabled(business_phone, user_phone):
        return FirebaseClient.fetch_data(f"establishments/{business_phone}/users/{user_phone}/ia_disabled") is True

    @staticmethod
    def toggle_ia_disabled(instance_name, business_phone, user_phone):
        ia_disabled_path = f"establishments/{business_phone}/users/{user_phone}/ia_disabled"
        ia_disabled_flag = FirebaseClient.fetch_data(ia_disabled_path) or False
        activated_message = "reativada" if ia_disabled_flag else "desativada"
        message = f"Asistente Virtual {activated_message} permanentemente."
        FirebaseClient.save_data(ia_disabled_path, not ia_disabled_flag)
        logger.warning(f"[handle_attendant_message] {message} para {user_phone} em {business_phone}")
        WhatsappService.send_evolution_response(instance_name, user_phone, message)
        ConversationHistoryService.append_message(business_phone, user_phone, "assistant", message)
