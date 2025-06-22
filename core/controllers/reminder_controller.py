import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.services.reminder_service import ReminderService
from core.utils.trace import set_trace_id, reset_trace_id

reminder_router = APIRouter()

logger = logging.getLogger(__name__)


@reminder_router.post("/reminder/execute")
async def execute_reminder():
    token = set_trace_id()
    try:
        logger.info(f"[execute_reminder] Executando lembretes")
        ReminderService.run()
        logger.info(f"[execute_reminder] Lembretes executados com sucesso")

        return JSONResponse(content={"status": "success"})
    except Exception as e:
        logger.exception(f"[execute_reminder]: Erro: {str(e)}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)
    finally:
        reset_trace_id(token)

