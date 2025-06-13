import logging
import os
import threading

import requests

logger = logging.getLogger(__name__)


class WhatsappService:

    @staticmethod
    def mark_message_as_read(instance_name, remote_jid, message_id):

        logger.debug(f"[mark_message_as_read] {instance_name} -> {remote_jid} -> {message_id}")
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

    @staticmethod
    def send_evolution_response(instance_name, to_number, message_text):
        logger.info(
            f"[Message Response] {instance_name} -> {to_number} -> {message_text}")
        try:
            api_key = os.environ.get('EVOLUTION_API_KEY')
            api_url = os.environ.get('EVOLUTION_API_URL')
            endpoint = f"{api_url}/message/sendText/{instance_name}"
            headers = {
                'apikey': api_key,
                'Content-Type': 'application/json'
            }
            to_number_formatted = to_number.split('@')[0] if '@' in to_number else to_number
            payload = {
                'number': to_number_formatted,
                'options': {'delay': 1200},
                'text': message_text
            }
            response = requests.post(endpoint, json=payload, headers=headers)
            if response.status_code not in [200, 201]:
                logger.error(f"Erro ao enviar mensagem: {response.text}")
            return response.json() if response.text else {'status': response.status_code}
        except Exception as e:
            logger.error(f"Erro ao enviar resposta: {str(e)}")
            return None

    @staticmethod
    def send_typing_signal(instance_name, to_number, duration_ms=10000):
        logger.debug(f"[send_typing_signal] {instance_name} -> {to_number}")
        threading.Thread(target=WhatsappService._send, args=(instance_name, to_number, duration_ms)).start()

    @staticmethod
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

            logger.debug(f"[TYPING] Enviando 'digitando...' para {to_number}")
            requests.post(typing_url, json=payload, headers=headers)


        except Exception as e:
            logger.error(f"[TYPING] Erro ao enviar sinal de typing: {str(e)}")
