import logging
import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

from core.controllers.admin_controller import admin_router
from core.controllers.health_controller import health_router
from core.controllers.whatsapp_controller import whatsapp_router
from core.dao.firebase_client import init_firebase, FirebaseClient
from core.services.buffer.buffer_collector import BufferCollector
from core.utils.constants import REPLICA_ID, get_environment
from core.utils.logger_config import setup_logger

setup_logger()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.debug(f"Iniciando instância com REPLICA_ID = {REPLICA_ID}")
    init_firebase()
    FirebaseClient.get_reference('healthcheck').set({"status": "ok", "timestamp": {".sv": "timestamp"}})
    logger.debug("Firebase inicializado com sucesso.")
    BufferCollector().start()
    logger.debug("BufferCollector inicializado com sucesso.")
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(health_router)
app.include_router(whatsapp_router)
app.include_router(admin_router)

if __name__ == "__main__":
    load_dotenv(override=True)

    required_vars = [
        'RAILWAY_ENVIRONMENT_NAME',
        'FIREBASE_CREDENTIALS_HOMOLOG',
        'EVOLUTION_API_KEY',
        'EVOLUTION_API_URL'
    ]

    for var in required_vars:
        if var not in os.environ:
            print(f"[ERRO] Variável de ambiente {var} não encontrada.")
            sys.exit(1)

    port = int(os.environ.get("PORT", 5000))

    logger.debug(f"Iniciando aplicação em ambiente: {get_environment()}")
    logger.debug(f"Iniciando FastAPI na porta {port}")

    uvicorn.run(
        app=app,
        host="0.0.0.0",
        port=port,
        reload=False,
        access_log=True,
        log_config=None
    )
