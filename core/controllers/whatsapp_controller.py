import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from core.controllers.dto.message_upsert_dto import MessageUpsertDTO
from core.controllers.dto.precense_update_dto import PresenceUpdateDTO
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
        if "data" not in payload:
            return JSONResponse(content={"status": "error", "message": "Dados inválidos"}, status_code=400)
        logger.debug(f"[evolution_messages_upsert] Payload: {payload}")
        incoming = MessageUpsertDTO(payload)
        IncomingService.handle_incoming_message(incoming)
        return JSONResponse(content={"status": "success"})
    except Exception as e:
        logger.error(f"[evolution_messages_upsert]: Erro: {str(e)}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)
