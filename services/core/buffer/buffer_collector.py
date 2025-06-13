import logging
import threading
import time

from dao.firebase_client import FirebaseClient
from services.core.buffer.buffer_service import BufferService
from services.core.whatsapp_service import WhatsappService
from utils.config import REPLICA_ID
from utils.trace import set_trace_id, reset_trace_id
from utils.whatsapp_chat_utils import send_typing_signal

PRESENCE_LAST_UPDATE_LIMIT_SECONDS = 60
PRESENCE_LAST_UPDATE_MINIMUM_FOR_PROCESS_SECONDS = 5
ZOMBIE_BUFFER_TIMEOUT_SECONDS = 5 * 60

logger = logging.getLogger(__name__)


def _should_ignore_buffer(user_phone: str, buffer: dict, now: int) -> bool:
    buffer_replica_id = buffer.get("replica_id", "")
    if REPLICA_ID != buffer_replica_id:
        return True
    presence = buffer.get("presence")
    presence_age = now - buffer.get("presence_last_updated", 0)
    if presence in ["composing", "recording"]:
        if presence_age < PRESENCE_LAST_UPDATE_LIMIT_SECONDS:
            logger.info(f"[Buffer Ignore] Ignorando {presence=} age={presence_age}s")
            return True
        else:
            logger.warning(
                f"[Buffer Force Available] Presença travada ({presence}) há {presence_age}s, forçando disponível")
            buffer["presence"] = "available"
            FirebaseClient.save_data(f"message_buffers/{user_phone}", buffer)
    if presence_age < PRESENCE_LAST_UPDATE_MINIMUM_FOR_PROCESS_SECONDS:
        logger.info(f"[Buffer Ignore] Ignorando porque presence age={presence_age}s (esperado >= 5s)")
        return True
    elif not buffer.get("messages"):
        return True
    return False


def _process_buffer(user_phone: str, buffer: dict):
    token = set_trace_id()
    logger.info(f"[_process_buffer] {user_phone} -> {buffer}")
    messages = buffer.get("messages", [])
    if not messages:
        return
    BufferService.clear_buffer(user_phone)
    instance_name = buffer.get("instance_name")
    business_phone = buffer.get("establishment_phone")
    send_typing_signal(instance_name, user_phone)

    full_message = ". ".join(messages).strip()
    logger.info(f"[Process Buffer] Processando mensagem de {user_phone} -> {instance_name}: {full_message}")

    response_text = WhatsappService.process_user_message(business_phone, full_message, user_phone, instance_name)

    if response_text:
        WhatsappService.send_evolution_response(instance_name, user_phone, response_text)
    reset_trace_id(token)


def _check_buffers():
    logger.info(f"[_check_buffers] Verificando buffers")
    now = int(time.time())
    buffers = BufferService.get_all_buffers()

    for user_phone, buffer in buffers.items():
        if _should_ignore_buffer(user_phone, buffer, now):
            continue
        _process_buffer(user_phone, buffer)


def _check_zombie_buffers():
    logger.info(f"[_check_zombie_buffers] Verificando buffers zumbis...")
    now = int(time.time())

    buffers = BufferService.get_all_buffers()

    for user_phone, buffer in buffers.items():
        replica_id_last_updated = buffer.get("replica_id_last_updated", 0)
        replica_id = buffer.get("replica_id", "")

        if now - replica_id_last_updated > ZOMBIE_BUFFER_TIMEOUT_SECONDS or not replica_id:
            logger.warning(
                f"[ZOMBIE BUFFER] Buffer zumbi encontrado para {user_phone}. Reassociando à réplica {REPLICA_ID}")

            updates = {
                "replica_id": REPLICA_ID,
                "last_updated": now,
                "replica_id_last_updated": now
            }

            BufferService.update_buffer(user_phone, updates)


class BufferCollector:
    CHECK_INTERVAL_SECONDS = 3  # segundos
    TIMEOUT_BUFFER_LAST_UPDATE_SECONDS = 30  # segundos

    def __init__(self):
        self._running = False
        self._thread = None

    def start(self):
        time.sleep(1)
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=False)
            self._thread.start()
            logger.info("BufferCollector iniciado.")

    def _run_loop(self):
        while self._running:
            try:
                _check_buffers()
                _check_zombie_buffers()
            except Exception as e:
                logger.error(f"Erro no BufferCollector: {str(e)}")
            time.sleep(self.CHECK_INTERVAL_SECONDS)
