import datetime
import logging

import pytz
from googleapiclient.errors import HttpError

from core.utils.constants import INTERNAL_DATE_FORMAT, INTERNAL_TIME_FORMAT, WEEKDAY_MAP, TIMEZONE

logger = logging.getLogger(__name__)


def parse_datetime(date_str, time_str, timezone):
    try:
        datetime_obj_local = datetime.datetime.strptime(
            f"{date_str} {time_str}",
            f"{INTERNAL_DATE_FORMAT} {INTERNAL_TIME_FORMAT}"
        )
        return timezone.localize(datetime_obj_local)
    except ValueError as ve:
        logger.error(f"Erro ao processar data/hora: {ve}")
        raise


def parse_date(date_str):
    try:
        return datetime.datetime.strptime(date_str, INTERNAL_DATE_FORMAT).date()
    except ValueError as ve:
        logger.error(f"Erro ao processar data: {ve}")
        raise


def get_day_time_range(date_obj, timezone):
    start_of_day = timezone.localize(datetime.datetime.combine(date_obj, datetime.time.min))
    end_of_day = timezone.localize(datetime.datetime.combine(date_obj, datetime.time.max))

    return (
        start_of_day.astimezone(pytz.utc),
        end_of_day.astimezone(pytz.utc)
    )


def get_event_duration(event):
    original_start = event['start'].get('dateTime')
    original_end = event['end'].get('dateTime')

    if not original_start or not original_end:
        return None

    original_start_dt_utc = datetime.datetime.fromisoformat(original_start.replace('Z', '+00:00'))
    original_end_dt_utc = datetime.datetime.fromisoformat(original_end.replace('Z', '+00:00'))
    duration = original_end_dt_utc - original_start_dt_utc
    return int(duration.total_seconds() // 60)


def get_event_times(events, timezone):
    booked_times = set()

    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))

        if start:
            try:
                start_dt_utc = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
                start_dt_local = start_dt_utc.astimezone(timezone)
                booked_time_str_local = start_dt_local.strftime(INTERNAL_TIME_FORMAT)
                booked_times.add(booked_time_str_local)
            except ValueError as ve:
                logger.error(f"Não foi possível processar o horário de início do evento: {start} - {ve}")
            except Exception as e:
                logger.error(f"Erro ao processar horário do evento: {e}")

    return booked_times


def get_weekday_pt(date_obj):
    weekday_requested = date_obj.strftime('%A')
    return WEEKDAY_MAP.get(weekday_requested, weekday_requested)


def create_event_body(professional_name_full, procedure, procedure_capacity, self_attendance_procedure, date_start,
                      date_end, user_name,
                      user_phone,
                      establishment_address):
    local_start = date_start.astimezone(TIMEZONE)
    formatted_date = local_start.strftime("%d/%m/%y às %H:%M")
    return {
        'summary': f'{formatted_date} - {user_name} - {procedure}',
        'description': f'Agendamento para {procedure} com {professional_name_full}. Cliente: {user_name}, Contato: {user_phone}',
        'location': establishment_address,
        'start': {
            'dateTime': date_start.isoformat(),
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': date_end.isoformat(),
            'timeZone': 'UTC',
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': 60},
            ],
        },
        'extendedProperties': {
            'private': {
                'created_by': "virtual_assistant",
                'user_phone': user_phone,
                'user_name': user_name,
                'procedure': procedure,
                'procedure_capacity': str(procedure_capacity),
                'self_attendance_procedure': self_attendance_procedure,
                'professional': professional_name_full,
            }
        }
    }


def find_event(service, calendar_id, date_str, time_str, timezone, procedure):
    try:
        localized_dt = parse_datetime(date_str, time_str, timezone)
        utc_dt = localized_dt.astimezone(pytz.utc)

        time_min = utc_dt.isoformat()
        time_max = (utc_dt + datetime.timedelta(minutes=1)).isoformat()

        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime',
            maxResults=1
        ).execute()
        events = events_result.get('items', [])

        if not events:
            return None
        procedure_events = [e for e in events if
                            ('extendedProperties' in e and
                             'private' in e['extendedProperties'] and
                             e['extendedProperties']['private'].get('procedure') == procedure)]
        if not procedure_events:
            return None
        found_event = procedure_events[0]
        start_time_found = found_event['start'].get('dateTime')

        if start_time_found:
            start_dt_found_utc = datetime.datetime.fromisoformat(start_time_found.replace('Z', '+00:00'))
            start_dt_found_local = start_dt_found_utc.astimezone(timezone)
            datetime_obj_local = localized_dt.replace(tzinfo=None)

            if (start_dt_found_local.hour == datetime_obj_local.hour and
                    start_dt_found_local.minute == datetime_obj_local.minute and
                    start_dt_found_local.date() == datetime_obj_local.date()):
                return found_event
            else:
                logger.warning(
                    f"Hora de início do evento ({start_dt_found_local}) não corresponde exatamente a data solicitada ({localized_dt}).")
                return None
        logger.warning(f"Evento encontrado não possui data/hora.")
        return None

    except ValueError as ve:
        logger.error(
            f"Erro ao processar data/hora em find_event (esperado {INTERNAL_DATE_FORMAT} {INTERNAL_TIME_FORMAT}): {ve}")
        return None
    except HttpError as he:
        logger.error(f"Erro na API do Google Calendar ao encontrar o evento: {he}")
        return None
    except Exception as e:
        logger.error(f"Um erro inesperado ocorreu ao encontrar o evento: {e}")
        return None


def find_events_at_slot(service, calendar_id, date_str, time_str, timezone, procedure, exclude_event_id=None):
    try:
        localized_dt = parse_datetime(date_str, time_str, timezone)
        utc_dt = localized_dt.astimezone(pytz.utc)

        time_min = utc_dt.isoformat()
        time_max = (utc_dt + datetime.timedelta(minutes=1)).isoformat()

        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime',
            maxResults=10
        ).execute()

        events = events_result.get('items', [])

        if exclude_event_id:
            events = [e for e in events if e.get('id') != exclude_event_id]
        procedure_events = [e for e in events if
                            ('extendedProperties' in e and
                             'private' in e['extendedProperties'] and
                             e['extendedProperties']['private'].get('procedure') == procedure)]
        other_procedure_events = [e for e in events if
                                  ('extendedProperties' in e and
                                   'private' in e['extendedProperties'] and
                                   e['extendedProperties']['private'].get('procedure') != procedure)]
        not_assistant_events = [e for e in events if
                                ('extendedProperties' not in e or
                                 'private' not in e['extendedProperties'] or
                                 e['extendedProperties']['private'].get('created_by') != "virtual_assistant")]

        return {"procedure_events": procedure_events,
                "other_procedure_events": other_procedure_events,
                "not_assistant_events": not_assistant_events}

    except Exception as e:
        logger.error(f"[count_events_at_slot] Erro ao contar eventos no horário {date_str} {time_str}: {e}")
        return 0
