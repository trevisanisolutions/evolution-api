import os
import uuid
from datetime import datetime

import pytz


def get_environment():
    return os.environ.get("RAILWAY_ENVIRONMENT_NAME")


ENVIRONMENT = os.environ.get("RAILWAY_ENVIRONMENT_NAME")

BUFFER_COLLECTOR_CHECK_INTERVAL_SECONDS = 3
PRESENCE_LAST_UPDATE_BEFORE_FORCE_AVAILABLE_TIMEOUT_SECONDS = 60
PRESENCE_LAST_UPDATE_MINIMUM_FOR_PROCESS_SECONDS = 5
ZOMBIE_BUFFER_TIMEOUT_SECONDS = 2 * 60

REPLICA_ID = str(uuid.uuid4())[:8]

INTERNAL_DATETIME_FORMAT = "%d/%m/%Y %H:%M"
INTERNAL_DATE_FORMAT = "%d/%m/%Y"
INTERNAL_TIME_FORMAT = "%H:%M"

DEFAULT_APPOINTMENT_DURATION_SECONDS = 60
DEFAULT_PROCEDURE_CAPACITY = 1

WEEKDAY_MAP = {
    'Monday': 'Segunda-feira',
    'Tuesday': 'Terça-feira',
    'Wednesday': 'Quarta-feira',
    'Thursday': 'Quinta-feira',
    'Friday': 'Sexta-feira',
    'Saturday': 'Sábado',
    'Sunday': 'Domingo'
}

TIMEZONE = pytz.timezone('America/Sao_Paulo')
TODAY = datetime.now(TIMEZONE).date()

GOOGLE_CALENDAR_CREDENTIALS_FILE = 'calendar_credentials.json'

AGENT_LAST_USED_TIMEOUT_SECONDS = 5 * 60 * 60

CONVERSATION_HISTORY_LIMIT = 50

HUMAN_ATTENDANT_LAST_UPDATE_TIMEOUT_SECONDS = 15 * 60

MAX_MESSAGE_LENGTH = 500

REUSE_THREAD_LAST_USED_TIMEOUT = 10 * 60

WEEK_DAYS = {
    0: "segunda-feira",
    1: "terça-feira",
    2: "quarta-feira",
    3: "quinta-feira",
    4: "sexta-feira",
    5: "sábado",
    6: "domingo"
}

MONTHS = {
    1: "janeiro",
    2: "fevereiro",
    3: "março",
    4: "abril",
    5: "maio",
    6: "junho",
    7: "julho",
    8: "agosto",
    9: "setembro",
    10: "outubro",
    11: "novembro",
    12: "dezembro"
}

RESET = "\033[0m"
COLORS = {
    "DEBUG": "\033[96m",
    "INFO": "\033[97m",
    "WARNING": "\033[93m",
    "ERROR": "\033[91m",
    "CRITICAL": "\033[91m"
}
