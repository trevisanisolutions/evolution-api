import logging

from google.auth.exceptions import DefaultCredentialsError
from google.oauth2 import service_account
from googleapiclient.discovery import build

from utils.file_path_utils import get_credential_path

GOOGLE_CALENDAR_CREDENTIALS_FILE = 'calendar_credentials.json'

logger = logging.getLogger(__name__)


def get_calendar_service():
    try:
        credentials = service_account.Credentials.from_service_account_file(
            get_credential_path(GOOGLE_CALENDAR_CREDENTIALS_FILE),
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        return build('calendar', 'v3', credentials=credentials)
    except (DefaultCredentialsError, FileNotFoundError):
        logger.error(
            f"Erro de credenciais: Arquivo de credenciais do Google Calendar não encontrado ou inválido em {GOOGLE_CALENDAR_CREDENTIALS_FILE}")
        return None
    except Exception as e:
        logger.error(f"Erro ao configurar o serviço do Google Calendar: {str(e)}")
        return None
