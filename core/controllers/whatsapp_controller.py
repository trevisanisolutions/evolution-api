import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from core.controllers.dto.message_upsert_dto import MessageUpsertDTO
from core.controllers.dto.precense_update_dto import PresenceUpdateDTO
from core.dao.firebase_client import FirebaseClient
from core.services.buffer.buffer_service import BufferService
from core.services.incoming_service import IncomingService

whatsapp_router = APIRouter()

logger = logging.getLogger(__name__)


@whatsapp_router.post("/whatsapp-evolution/presence-update")
async def evolution_presence_update(request: Request):
    try:
        data = await request.json()
        incoming = PresenceUpdateDTO(data)
        user_phone, last_presence = incoming.get_user_presence_info()
        logger.debug(f"[evolution_presence_update] {user_phone} -> {last_presence}")
        user_buffer = FirebaseClient.fetch_data(f"message_buffers/{user_phone}")
        if not user_buffer:
            logger.warning(f"[evolution_presence_update] Não encontrado buffer para usuário: {user_phone}")
            return JSONResponse(content={"status": "success"})
        BufferService.update_presence_to_buffer(user_phone, last_presence)
        return JSONResponse(content={"status": "success"})
    except ValueError as ve:
        logger.warning(f"[evolution_presence_update]: Dados inválidos: {str(ve)}")
        return JSONResponse(content={"status": "error", "message": str(ve)}, status_code=400)
    except Exception as e:
        logger.exception(f"[evolution_presence_update]: Erro: {str(e)}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


@whatsapp_router.post("/whatsapp-evolution/messages-upsert")
async def evolution_messages_upsert(request: Request):
    try:
        payload = await request.json()
        logger.debug(f"[evolution_messages_upsert] Payload: {payload}")
        incoming = MessageUpsertDTO(payload)
        if _is_area_code_not_permitted(incoming.user_phone_area_code, incoming.business_phone):
            logger.warning(
                f"[evolution_messages_upsert] Telefone diferente do código de área permitido: {incoming.user_phone}")
            return JSONResponse(content={"status": "success"})
        IncomingService.handle_incoming_message(incoming)
        return JSONResponse(content={"status": "success"})
    except ValueError as ve:
        logger.warning(f"[evolution_messages_upsert] Dados inválidos: {str(ve)}")
        return JSONResponse(content={"status": "error", "message": str(ve)}, status_code=400)
    except Exception as e:
        logger.error(f"[evolution_messages_upsert]: Erro: {str(e)}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


def _is_area_code_not_permitted(user_phone_area_code: str, business_phone: str) -> bool:
    config_path = f"establishments/{business_phone}/config"
    establishment_config = FirebaseClient.fetch_data(config_path)

    if not establishment_config:
        logger.warning(
            f"[Código de Área] Configuração não encontrada para o estabelecimento: {business_phone}")
        return False

    allowed_codes = establishment_config.get("allowed_phone_area_codes")

    if not allowed_codes:
        logger.warning(
            f"[Código de Área] Nenhum código de área permitido configurado para o estabelecimento: {business_phone}")
        return False

    logger.debug(f"[_not_permitted_phone_are_code] Códigos de área permitidos: {allowed_codes}")
    logger.debug(f"[_not_permitted_phone_are_code] Código de área do usuário: {user_phone_area_code}")

    if user_phone_area_code in allowed_codes:
        return False

    return True
