import json
import logging
import re

from pydantic import ValidationError

from services.sec24.registration.dto.user_registration_dto import UserRegistrationDTO
from services.sec24.registration.user_formatter import UserFormatter
from services.sec24.sec24_client import SEC24ApiClient

logger = logging.getLogger(__name__)


class SEC24UserService:

    @staticmethod
    def register_user(data: dict) -> str:
        try:
            dto = UserRegistrationDTO(**data)

            token = SEC24ApiClient.get_auth_token()
            if not token:
                return SEC24UserService._json_error("Falha na autenticação com a API da SEC24.")

            user_payload = UserFormatter.to_api_payload(dto)
            response = SEC24ApiClient.create_user(token, user_payload)

            if response and response.status_code in [200, 201]:
                return SEC24UserService._json_success(f"Usuário '{dto.nome}' cadastrado com sucesso.")
            else:
                return SEC24UserService._json_error(
                    f"Erro ao cadastrar usuário. ({response.status_code}) {response.text if response else 'Sem resposta'}"
                )

        except ValidationError as e:
            return SEC24UserService._json_error(f"Erro de validação: {str(e)}")
        except Exception as e:
            logger.exception("Erro inesperado no cadastro")
            return SEC24UserService._json_error(f"Exceção: {str(e)}")

    @staticmethod
    def check_registration(params):
        try:
            cpf = params.get('cpf', '')
            if not cpf:
                return json.dumps({"exists": False, "message": "CPF não informado. Por favor, informe um CPF válido."})

            cpf_formatado = re.sub(r'\D', '', cpf)[:11]
            token = SEC24ApiClient.get_auth_token()
            if not token:
                return json.dumps({"exists": False, "message": "Falha ao autenticar com a API da SEC24."})

            response = SEC24ApiClient.find_user_by_cpf(token, cpf_formatado)
            if response and response.status_code == 200:
                data = response.json()
                if data.get("totalCount", 0) > 0:
                    return json.dumps({"exists": True, "message": "Usuário já cadastrado na SEC24."})
                else:
                    return json.dumps({"exists": False, "message": "CPF não encontrado na base de dados."})

            return json.dumps({"exists": False, "message": "Erro ao consultar cadastro. Tente novamente mais tarde."})

        except Exception as e:
            logger.error(f"Erro durante verificação de CPF: {str(e)}")
            return json.dumps({"exists": False, "message": f"Erro: {str(e)}"})

    @staticmethod
    def _json_success(msg):
        return json.dumps({"status": "success", "message": msg})

    @staticmethod
    def _json_error(msg):
        return json.dumps({"status": "error", "message": msg})
