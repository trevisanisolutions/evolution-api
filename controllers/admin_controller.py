# Atualizado: controllers/admin_controller.py

import logging

from fastapi import APIRouter, HTTPException

from dao.firebase_client import FirebaseClient

admin_router = APIRouter()
logger = logging.getLogger(__name__)


@admin_router.delete("/admin/purge/user/{user_phone}")
def purge_user_data(user_phone: str):
    try:
        deleted_paths = []

        establishments = FirebaseClient.fetch_data("establishments")
        for establishment_phone, establishment_data in establishments.items():
            establishment_id = establishment_data["id"]
            user_path = f"establishments/{establishment_id}/users/{user_phone}"
            if FirebaseClient.delete_data(user_path):
                deleted_paths.append(user_path)

        user_buffer_path = f"message_buffers/{user_phone}"
        if FirebaseClient.delete_data(user_buffer_path):
            deleted_paths.append(user_buffer_path)

        logger.info(f"[ADMIN] Dados do usuário {user_phone} removidos: {deleted_paths}")
        return {"status": "success", "deleted": deleted_paths}

    except Exception as e:
        logger.error(f"[ADMIN] Erro ao apagar dados do usuário {user_phone}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao apagar dados do usuário: {str(e)}")


@admin_router.delete("/admin/purge/establishment/{establishment_phone}")
def purge_establishment_data(establishment_phone: str):
    try:
        deleted_paths = []
        delete_path = f"establishments/{establishment_phone}/users"
        if FirebaseClient.delete_data(delete_path):
            deleted_paths.append(delete_path)

        logger.info(f"[ADMIN] Dados de usuários do estabelecimento {establishment_phone} removidos: {deleted_paths}")
        return {"status": "success", "deleted": deleted_paths}

    except Exception as e:
        logger.error(f"[ADMIN] Erro ao apagar dados de usuários do estabelecimento {establishment_phone}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao apagar dados do usuário: {str(e)}")


@admin_router.delete("/admin/clear-replica-ids")
def clear_all_replica_ids():
    try:
        buffers = FirebaseClient.fetch_data("message_buffers") or {}
        cleared = []

        for user_phone, data in buffers.items():
            updates = {
                "replica_id": None,
            }
            FirebaseClient.update_data(f"message_buffers/{user_phone}", updates)
            cleared.append(user_phone)

        logger.info(f"[ADMIN] replica_id limpo de {len(cleared)} usuários: {cleared}")
        return {"status": "success", "cleared_users": cleared}

    except Exception as e:
        logger.error(f"[ADMIN] Erro ao limpar replica_ids: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao limpar replica_ids: {str(e)}")
