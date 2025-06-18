import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.services.reminder_service import ReminderService

reminder_router = APIRouter()

logger = logging.getLogger(__name__)


@reminder_router.post("/reminder/execute")
async def execute_reminder():
    try:
        logger.info(f"[execute_reminder] Executando lembretes")
        ReminderService.run()
        logger.info(f"[execute_reminder] Lembretes executados com sucesso")

        return JSONResponse(content={"status": "success"})
    except Exception as e:
        logger.exception(f"[execute_reminder]: Erro: {str(e)}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)
