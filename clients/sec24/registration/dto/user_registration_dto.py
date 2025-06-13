from pydantic import BaseModel


class UserRegistrationDTO(BaseModel):
    nome: str
    cpf: str
    email: str
    telefone: str
    cep: str
    estado: str
    cidade: str
    bairro: str
    endereco: str
    numero: str
    complemento: str | None = None
    pais: str = "Brasil"
