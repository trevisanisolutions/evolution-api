import logging
import os
import threading

import requests

logger = logging.getLogger(__name__)


def send_typing_signal(instance_name, to_number, duration_ms=10000):
    """
    Envia um sinal de "digitando..." para o número do usuário usando a Evolution API.

    Esse envio é feito em uma thread separada para não bloquear o fluxo principal.
      """
    logger.info(f"[send_typing_signal] {instance_name} -> {to_number}")
    threading.Thread(target=_send, args=(instance_name, to_number, duration_ms)).start()


def _send(instance_name, to_number, duration_ms):
    try:
        if '@' in to_number:
            to_number = to_number.split('@')[0]

        api_key = os.environ.get('EVOLUTION_API_KEY')
        api_url = os.environ.get('EVOLUTION_API_URL')

        headers = {
            'apikey': api_key,
            'Content-Type': 'application/json'
        }

        typing_url = f"{api_url.rstrip('/')}/chat/sendPresence/{instance_name}"

        payload = {
            'number': to_number,
            'delay': duration_ms,
            'presence': 'composing'
        }

        logger.info(f"[TYPING] Enviando 'digitando...' para {to_number}")
        response = requests.post(typing_url, json=payload, headers=headers)
        logger.info(f"[TYPING] Status: {response.status_code}")
        logger.info(f"[TYPING] Body: {response.text}")

    except Exception as e:
        logger.error(f"[TYPING] Erro ao enviar sinal de typing: {str(e)}")


def mark_message_as_read(instance_name, remote_jid, message_id):
    """
    Marca uma mensagem específica como lida via Evolution API.

    Args:
        instance_name (str): Nome da instância da Evolution.
        remote_jid (str): Ex: '5511999999999@s.whatsapp.net'
        message_id (str): ID da mensagem recebida no webhook.
    """

    logger.info(f"[mark_message_as_read] {instance_name} -> {remote_jid} -> {message_id}")
    try:
        api_key = os.environ.get('EVOLUTION_API_KEY')
        api_url = os.environ.get('EVOLUTION_API_URL')
        headers = {
            'apikey': api_key,
            'Content-Type': 'application/json'
        }
        url = f"{api_url.rstrip('/')}/chat/markMessageAsRead/{instance_name}"
        payload = {
            "readMessages": [
                {
                    "remoteJid": remote_jid,
                    "fromMe": False,
                    "id": message_id
                }
            ]
        }

        response = requests.post(url, json=payload, headers=headers)
        return response.status_code in (200, 201)

    except Exception as e:
        logger.error(f"[READ] Erro ao marcar mensagem como lida: {str(e)}")
        return False
