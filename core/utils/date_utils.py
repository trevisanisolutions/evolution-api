import datetime
from functools import lru_cache

import requests

from core.utils.constants import WEEK_DAYS, MONTHS


def get_today_formated():
    hoje = datetime.datetime.now()

    week_day = WEEK_DAYS[hoje.weekday()]
    day = hoje.day
    month = MONTHS[hoje.month]
    year = hoje.year

    return f"{week_day.capitalize()}, {day} de {month} de {year}"


@lru_cache(maxsize=3)
def get_holidays(year: str) -> str:
    url = f"https://brasilapi.com.br/api/feriados/v1/{year}?estado=RS&municipio=porto_alegre"  # TODO: receber parametros de estado e município do assistente
    response = requests.get(url)
    return response.json()
