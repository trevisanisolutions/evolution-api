import datetime
from functools import lru_cache

import requests

week_days = {
    0: "segunda-feira",
    1: "terça-feira",
    2: "quarta-feira",
    3: "quinta-feira",
    4: "sexta-feira",
    5: "sábado",
    6: "domingo"
}

months = {
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


def get_today_formated():
    hoje = datetime.datetime.now()

    week_day = week_days[hoje.weekday()]
    day = hoje.day
    month = months[hoje.month]
    year = hoje.year

    return f"{week_day.capitalize()}, {day} de {month} de {year}"


@lru_cache(maxsize=3)
def get_holidays(year: str) -> str:
    url = f"https://brasilapi.com.br/api/feriados/v1/{year}?estado=RS&municipio=porto_alegre"  # TODO: receber parametros de estado e município do assistente
    response = requests.get(url)
    return response.json()
