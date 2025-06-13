import re
from datetime import datetime

from clients.sec24.registration.dto.user_registration_dto import UserRegistrationDTO


class UserFormatter:
    @staticmethod
    def to_api_payload(dto: UserRegistrationDTO) -> dict:
        now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')
        return {
            "nome": dto.nome,
            "dat_nascimento_fundacao": now,
            "cpf_cnpj": re.sub(r'\D', '', dto.cpf)[:11],
            "tipo_usuario_id": 3,
            "pessoa_email": [{"email": dto.email}],
            "pessoa_telefone": [{"telefone": re.sub(r'\D', '', dto.telefone)[:11]}],
            "pessoa_endereco": {
                "cep": dto.cep,
                "pais": dto.pais,
                "estado": dto.estado,
                "cidade": dto.cidade,
                "bairro": dto.bairro,
                "endereco": dto.endereco,
                "numero": dto.numero,
                "complemento": dto.complemento or ""
            }
        }
