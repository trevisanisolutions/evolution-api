# controllers/health_controller.py

import datetime
import logging
import os
import socket

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from dao.firebase_client import FirebaseClient

health_router = APIRouter()
logger = logging.getLogger(__name__)


@health_router.get("/health")
async def health_check():
    try:
        environment_name = os.environ.get('RAILWAY_ENVIRONMENT_NAME')
        firebase_ok = _check_firebase_connection()

        system_info = {
            "hostname": socket.gethostname(),
            "ip_address": socket.gethostbyname(socket.gethostname()),
            "timestamp": datetime.datetime.now().isoformat(),
            "environment": environment_name,
            "version": os.environ.get('APP_VERSION')
        }

        response = {
            "status": "ok" if firebase_ok else "degraded",
            "timestamp": system_info["timestamp"],
            "environment": system_info["environment"],
            "version": system_info["version"],
            "hostname": system_info["hostname"],
            "ip": system_info["ip_address"],
            "dependencies": {
                "firebase": "ok" if firebase_ok else "error"
            }
        }

        return JSONResponse(content=response, status_code=200 if firebase_ok else 503)

    except Exception as e:
        return JSONResponse(content={
            "status": "error",
            "message": str(e),
            "timestamp": datetime.datetime.now().isoformat()
        }, status_code=503)


def _check_firebase_connection():
    try:
        ref = FirebaseClient.get_reference('healthcheck_status')
        ref.get()
        return True
    except Exception as e:
        logger.error(f"Erro ao verificar conexão com Firebase: {str(e)}")
        return False
