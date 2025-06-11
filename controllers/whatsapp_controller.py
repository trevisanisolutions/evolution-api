# controllers/whatsapp_controller.py
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from soupsieve.util import lower

from controllers.dto.message_upsert_dto import MessageUpsertDTO
from controllers.dto.precense_update_dto import PresenceUpdateDTO
from dao.firebase_client import FirebaseClient
from services.core.buffer.buffer_service import BufferService
from services.core.whatsapp_service import WhatsappService

whatsapp_router = APIRouter()

logger = logging.getLogger(__name__)
MAX_MESSAGE_LENGTH = 500


def is_attendance_active(establishment_phone: str, user_phone: str) -> bool:
    attendance = FirebaseClient.fetch_data(
        f"establishments/{establishment_phone}/users/{user_phone}/human_attendance") or {}
    return attendance.get("active", False)


@whatsapp_router.post("/whatsapp-evolution/presence-update")
async def handle_presence_update(request: Request):
    try:
        data = await request.json()
        incoming = PresenceUpdateDTO(data)

        user_phone, last_presence = incoming.get_user_presence_info()
        logger.info(f"[handle_presence_update] {user_phone} -> {last_presence}")

        BufferService.update_presence(user_phone, last_presence, incoming.instance_name)

        return JSONResponse(content={"status": "success"})

    except ValueError as ve:
        logger.warning(f"[handle_presence_update]: Dados inválidos: {str(ve)}")
        return JSONResponse(content={"status": "error", "message": str(ve)}, status_code=400)

    except Exception as e:
        logger.exception(f"[handle_presence_update]: Erro: {str(e)}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


@whatsapp_router.post("/whatsapp-evolution/messages-upsert")
async def handle_evolution_whatsapp(request: Request):
    try:
        payload = await request.json()
        if "data" not in payload:
            return JSONResponse(content={"status": "error", "message": "Dados inválidos"}, status_code=400)

        incoming = MessageUpsertDTO(payload)
        logger.info(
            f"[handle_evolution_whatsapp] {incoming.user_phone if not incoming.from_me else '[Atendente Humano]'} → {incoming.instance_name if not incoming.from_me else incoming.user_phone}: {incoming.user_msg}")
        if not incoming.user_msg:
            logger.warning(f"[handle_evolution_whatsapp] Mensagem vazia recebida de {incoming.user_phone}")
            return JSONResponse(content={"status": "success"})
        if len(incoming.user_msg) > MAX_MESSAGE_LENGTH:
            user_resp = (
                "Opa! Sua mensagem é muito longa para processarmos de uma vez. "
                "Por favor, divida sua mensagem em partes menores ou seja mais específico. "
                "Isso nos ajuda a atendê-lo melhor e mais rapidamente."
            )
            return WhatsappService.send_evolution_response(incoming.instance_name, incoming.user_phone, user_resp)

        if "reset" == lower(incoming.user_msg):
            FirebaseClient.delete_data(f"establishments/{incoming.business_phone}/users/{incoming.user_phone}")
            FirebaseClient.delete_data(f"message_buffers/{incoming.user_phone}")
            logger.warning(f"Contexto resetado: {incoming.user_phone}")
            return WhatsappService.send_evolution_response(incoming.instance_name, incoming.user_phone,
                                                           "Contexto resetado com sucesso.")
        WhatsappService.process_incoming_message(incoming)

        return JSONResponse(content={"status": "success"})


    except Exception as e:
        logger.error(f"[handle_evolution_whatsapp]: Erro: {str(e)}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)
