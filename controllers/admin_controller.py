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
            user_path = f"establishments/{establishment_phone}/users/{user_phone}"
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


@admin_router.delete("/admin/purge/establishment/{establishment_phone}/users")
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


@admin_router.delete("/admin/purge/establishment/{establishment_phone}/users/threads/{agent_name}")
def clear_agent_threads(establishment_id: str, agent_name: str):
    try:
        users = FirebaseClient.fetch_data(f"/establishments/{establishment_id}/users")

        if not users:
            raise HTTPException(status_code=404, detail="Nenhum usuário encontrado para esse estabelecimento.")

        for user_phone, user_data in users.items():
            FirebaseClient.delete_data(
                f"/establishments/{establishment_id}/users/{user_phone}/conversations/threads/{agent_name}")
        return {"success": True, "message": f"Threads do agente '{agent_name}' removidos com sucesso."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao limpar threads: {str(e)}")


@admin_router.delete("/admin/buffers/clear-replica-ids")
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
