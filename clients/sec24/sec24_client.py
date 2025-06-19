import logging
import re

import requests

from core.utils.constants import get_environment

logger = logging.getLogger(__name__)


class SEC24ApiClient:
    BASE_URL = "https://app.sec24.com.br" if get_environment() == 'production' else "https://dev.sec24.com.br"
    AUTH_BASE_URL = f"https://sso.sec24.com.br" if get_environment() == 'production' else {BASE_URL}
    AUTH_URL = f"{AUTH_BASE_URL}:8443/realms/saudeemcasa/protocol/openid-connect/token" if get_environment() == 'production' else f"{BASE_URL}/auth/realms/saudeemcasa/protocol/openid-connect/token"
    AUTH_HEADER = "Basic YXNzaXN0YW50LWNoYXQtc2VydmljZTpyQWRnRTZDVjZ5a0thWFJEeFRiS3p5cXAxWDZFQ25FdQ==" if get_environment() == 'production' else "Basic YXNzaXN0YW50LWNoYXQtc2VydmljZTpZYzNrQVRKRHRoVzlJNTVqZlpqaHRLRHJzUFpnRnpvbg=="

    @staticmethod
    def get_auth_token():
        try:
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "Authorization": SEC24ApiClient.AUTH_HEADER
            }
            data = {"grant_type": "client_credentials"}
            logger.debug(f"[get_auth_token]: {SEC24ApiClient.AUTH_URL}, headers: {headers}, data: {data}")
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
            logger.debug(f"[create_user]: {url}, headers: {headers}, user_data: {user_data}")
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
            logger.debug(f"[find_user_by_cpf]: {url}, headers: {headers}, formatted_cpf: {formatted_cpf}")
            return requests.get(url, headers=headers)
        except Exception as e:
            logger.error(f"Erro ao buscar usuário por CPF: {str(e)}")
            return None
