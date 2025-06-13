import logging
import re

import requests

logger = logging.getLogger(__name__)


# TODO: Verificar URLs de produção
class SEC24ApiClient:
    BASE_URL = "https://dev.sec24.com.br"
    AUTH_URL = f"{BASE_URL}/auth/realms/saudeemcasa/protocol/openid-connect/token"
    AUTH_HEADER = "Basic YXNzaXN0YW50LWNoYXQtc2VydmljZTpZYzNrQVRKRHRoVzlJNTVqZlpqaHRLRHJzUFpnRnpvbg=="

    @staticmethod
    def get_auth_token():
        try:
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "Authorization": SEC24ApiClient.AUTH_HEADER
            }
            data = {"grant_type": "client_credentials"}
            response = requests.post(SEC24ApiClient.AUTH_URL, headers=headers, data=data)
            if response.status_code == 200:
                return response.json().get("access_token")
            else:
                logger.error(f"Token error: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Token exception: {str(e)}")
        return None

    @staticmethod
    def create_user(token, user_data):
        try:
            url = f"{SEC24ApiClient.BASE_URL}/server/chat-secretariado/criar-usuario"
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            return requests.post(url, headers=headers, json=user_data)
        except Exception as e:
            logger.error(f"Create user exception: {str(e)}")
            return None

    @staticmethod
    def find_user_by_cpf(token, cpf):
        try:
            formatted_cpf = re.sub(r'\D', '', cpf)[:11]
            url = f"{SEC24ApiClient.BASE_URL}/server/chat-secretariado/listar-usuarios?pageSize=1&search={formatted_cpf}&page=1"
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }
            return requests.get(url, headers=headers)
        except Exception as e:
            logger.error(f"Erro ao buscar usuário por CPF: {str(e)}")
            return None
