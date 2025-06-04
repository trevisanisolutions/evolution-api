# firebase_client.py
import json
import logging
import os

import firebase_admin
from firebase_admin import credentials, db

from utils.base64_utils import decode_text

logger = logging.getLogger(__name__)
_firebase_instances = {}


def get_environment():
    return os.environ.get('RAILWAY_ENVIRONMENT_NAME', 'development')


def init_firebase():
    """Inicializa a conexão com o Firebase para o ambiente corrente"""
    environment_name = get_environment()

    if environment_name in _firebase_instances:
        return _firebase_instances[environment_name]

    logger.info(f"Inicializando Firebase para ambiente: {environment_name}")

    try:
        if environment_name == 'production':
            firebase_creds_b64 = os.environ.get('FIREBASE_CREDENTIALS')
            db_url = os.environ.get('FIREBASE_URL')
        else:
            firebase_creds_b64 = os.environ.get('FIREBASE_CREDENTIALS_HOMOLOG')
            db_url = os.environ.get('FIREBASE_URL_HOMOLOG')

        if not firebase_creds_b64 or not db_url:
            raise ValueError("Credenciais ou URL do Firebase não encontradas nas variáveis de ambiente")

        cred_json = decode_base64_credentials(firebase_creds_b64)
        cred = credentials.Certificate(cred_json)
        firebase_app = firebase_admin.initialize_app(cred, {'databaseURL': db_url}, name=environment_name)
        _firebase_instances[environment_name] = firebase_app
        return firebase_app
    except Exception as e:
        logger.error(f"Erro ao inicializar Firebase: {str(e)}")
        raise


def decode_base64_credentials(base64_str):
    try:
        decoded_str = decode_text(base64_str)
        return json.loads(decoded_str)
    except Exception as e:
        logger.error(f"Erro ao decodificar credenciais Base64: {str(e)}")
        raise ValueError(f"Erro ao decodificar credenciais em Base64: {str(e)}")


class FirebaseClient:
    @staticmethod
    def _get_app():
        environment = get_environment()
        if environment not in _firebase_instances:
            init_firebase()
        try:
            return firebase_admin.get_app(name=environment)
        except ValueError:
            return init_firebase()

    @staticmethod
    def get_reference(path):
        app = FirebaseClient._get_app()
        return db.reference(path, app=app)

    @staticmethod
    def fetch_data(path):
        try:
            ref = FirebaseClient.get_reference(path)
            return ref.get()
        except Exception as e:
            logger.error(f"Erro ao buscar dados de '{path}': {str(e)}")
            return None

    @staticmethod
    def save_data(path, data):
        try:
            ref = FirebaseClient.get_reference(path)
            ref.set(data)
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar dados em '{path}': {str(e)}")
            return False

    @staticmethod
    def update_data(path, updates):
        try:
            ref = FirebaseClient.get_reference(path)
            ref.update(updates)
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar dados em '{path}': {str(e)}")
            return False

    @staticmethod
    def delete_data(path):
        try:
            ref = FirebaseClient.get_reference(path)
            ref.delete()
            return True
        except Exception as e:
            logger.error(f"Erro ao excluir dados de '{path}': {str(e)}")
            return False

    @staticmethod
    def push_data(path, data):
        try:
            ref = FirebaseClient.get_reference(path)
            new_ref = ref.push()
            new_ref.set(data)
            return new_ref.key
        except Exception as e:
            logger.error(f"Erro ao inserir dados em '{path}': {str(e)}")
            return None
