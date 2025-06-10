import datetime
import logging
from datetime import datetime, timedelta, timezone as tz

import pytz
from googleapiclient.errors import HttpError

from services.calendar.client import get_calendar_service
from services.calendar.constants import INTERNAL_DATE_FORMAT, INTERNAL_TIME_FORMAT, DEFAULT_APPOINTMENT_DURATION, \
    DEFAULT_PROCEDURE_CAPACITY
from services.calendar.utils import parse_date, parse_datetime, find_event, get_event_duration, create_event_body, \
    get_weekday_pt, get_day_time_range
from utils.date_utils import get_holidays
from utils.tool_response import json_success, json_error, json_partial_success

logger = logging.getLogger(__name__)


def is_slot_available(start, end, events, timezone, user_phone, procedure_name, is_self_attendance, procedure_capacity):
    same_procedure_count = 0
    for event in events:
        try:
            start_ev = event['start'].get('dateTime')
            end_ev = event['end'].get('dateTime')
            if not start_ev or not end_ev:
                continue

            start_dt = datetime.fromisoformat(start_ev).astimezone(timezone)
            end_dt = datetime.fromisoformat(end_ev).astimezone(timezone)

            if max(start, start_dt) < min(end, end_dt):
                is_external = (
                        'extendedProperties' not in event or
                        'private' not in event['extendedProperties'] or
                        event['extendedProperties']['private'].get('created_by') != 'virtual_assistant'
                )
                if is_external:
                    return False, "Horário ocupado por evento externo."

                if event['extendedProperties']['private'].get('user_phone') == user_phone:
                    return False, "Você já possui um agendamento que coincide com este horário."

                if event['extendedProperties']['private'].get('procedure') == procedure_name:
                    same_procedure_count += 1
                elif not is_self_attendance and not (
                        event['extendedProperties']['private'].get('self_attendance_procedure',
                                                                   "false").lower() == 'true'):
                    return False, "Profissional já está atendendo outro procedimento."
        except Exception as e:
            logger.warning(f"[is_slot_available] Erro ao processar evento: {e}")
    if same_procedure_count >= procedure_capacity:
        return False, "Capacidade máxima atingida para esse procedimento."
    return True, None


def check_availability(args):
    professional_name = args.get("professional_name")
    professional_calendar_id = args.get("professional_calendar_id")
    procedure_name = args.get("procedure_name")
    procedure_duration_minutes = args.get("procedure_duration_minutes")
    procedure_capacity = args.get("procedure_capacity")
    is_self_attendance = str(args.get("self_attendance_procedure", "false")).lower() == "true"
    date = args.get("date")
    user_phone = args.get("user_phone")
    work_schedule = args.get("work_schedule")
    step_minutes = args.get("step_minutes")

    service = get_calendar_service()
    timezone = pytz.timezone("America/Sao_Paulo")

    try:
        date_obj = parse_date(date)
        weekday_pt = get_weekday_pt(date_obj)

        schedules_today = [ws for ws in work_schedule if ws["weekday"].lower() == weekday_pt.lower()]
        if not schedules_today:
            return {
                "success": False,
                "message": f"{professional_name} não trabalha em {weekday_pt}, {date}.",
                "slot": {"date": date}
            }

        def generate_flexible_time_slots(start: str, end: str):
            time_format = "%H:%M"
            start_time = timezone.localize(datetime.combine(date_obj, datetime.strptime(start, time_format).time()))
            end_time = timezone.localize(datetime.combine(date_obj, datetime.strptime(end, time_format).time()))
            slots = []
            current = start_time
            step = timedelta(minutes=int(step_minutes)) if step_minutes else timedelta(minutes=1)
            while (current + timedelta(minutes=procedure_duration_minutes)) <= end_time:
                slot_start = current
                slot_end = current + timedelta(minutes=procedure_duration_minutes)
                slots.append((slot_start, slot_end))
                current += step
            return slots

        all_slots = []
        for schedule in schedules_today:
            all_slots.extend(generate_flexible_time_slots(
                schedule["start_time"],
                schedule["end_time"]
            ))

        start_utc, end_utc = get_day_time_range(date_obj, timezone)
        events_result = service.events().list(
            calendarId=professional_calendar_id,
            timeMin=start_utc.isoformat(),
            timeMax=end_utc.isoformat(),
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        events = events_result.get("items", [])

        truly_available_slots = []
        reasons = []
        for slot_start, slot_end in all_slots:
            is_available, reason = is_slot_available(
                slot_start,
                slot_end,
                events,
                timezone,
                user_phone,
                procedure_name,
                is_self_attendance,
                procedure_capacity
            )
            if is_available:
                truly_available_slots.append(slot_start.strftime("%H:%M"))
            else:
                reasons.append(reason)

        if not truly_available_slots:
            return {
                "success": False,
                "message": f"Não há horários disponíveis para {procedure_name} com {professional_name} em {date}. Monivo(s): {', '.join(reasons)}",
                "slot": {"date": date}
            }

        formatted = [t.replace(":", "h") for t in truly_available_slots]
        holidays = get_holidays(date_obj.year)
        for holiday in holidays:
            if holiday['date'] == date_obj.strftime("%Y-%m-%d"):
                return {
                    "success": False,
                    "message": f"A data {date} é um feriado: {holiday['name']}.",
                    "slot": {"date": date}
                }
        return {
            "success": True,
            "message": f"Horários disponíveis para {procedure_name} com {professional_name} em {date}: {', '.join(formatted)}",
            "slot": {"date": date}
        }

    except ValueError as ve:
        logger.error(f"[check_availability] Erro de data: {ve}")
        return {
            "success": False,
            "message": f"Formato inválido de data. Use DD/MM/AAAA. Detalhes: {ve}",
            "slot": {"date": date}
        }
    except HttpError as he:
        logger.error(f"[check_availability] Erro na API do Google Calendar: {he}")
        return {
            "success": False,
            "message": f"Ocorreu um erro ao consultar a agenda: {he}",
            "slot": {"date": date}
        }
    except Exception as e:
        logger.error(f"[check_availability] Erro inesperado: {e}")
        return {
            "success": False,
            "message": f"Ocorreu um erro inesperado: {e}",
            "slot": {"date": date}
        }


def create_appointment(args):
    address = args.get("address")
    user_phone = args.get("user_phone")
    professional_name = args.get("professional_name")
    professional_calendar_id = args.get("professional_calendar_id")
    date = args.get("date")
    time = args.get("time")
    procedure = args.get("procedure")
    user_name = args.get("user_name")
    self_attendance_procedure = str(args.get("self_attendance_procedure", "false")).lower() == "true"
    procedure_duration_minutes = args.get("procedure_duration_minutes", DEFAULT_APPOINTMENT_DURATION)
    procedure_capacity = int(args.get("procedure_capacity", DEFAULT_PROCEDURE_CAPACITY))

    service = get_calendar_service()
    timezone = pytz.timezone("America/Sao_Paulo")

    try:
        localized_dt = parse_datetime(date, time, timezone)
        utc_dt = localized_dt.astimezone(tz.utc)
        end_dt = utc_dt + timedelta(minutes=procedure_duration_minutes)

        start_utc, end_utc = get_day_time_range(localized_dt.date(), timezone)
        events = service.events().list(
            calendarId=professional_calendar_id,
            timeMin=start_utc.isoformat(),
            timeMax=end_utc.isoformat(),
            singleEvents=True,
            orderBy="startTime"
        ).execute().get("items", [])
        is_available, reason = is_slot_available(
            localized_dt,
            localized_dt + timedelta(minutes=procedure_duration_minutes),
            events,
            timezone,
            user_phone,
            procedure,
            self_attendance_procedure,
            procedure_capacity
        )
        if not is_available:
            return {
                "success": False,
                "message": f"{date} às {time}: {reason}",
                "slot": {"date": date, "time": time}
            }

        event = create_event_body(
            professional_name,
            procedure,
            procedure_capacity,
            self_attendance_procedure,
            utc_dt,
            end_dt,
            user_name,
            user_phone,
            address
        )
        service.events().insert(calendarId=professional_calendar_id, body=event).execute()

        return {
            "success": True,
            "message": f"{date} às {time}: Agendamento confirmado para {procedure} com {professional_name}.",
            "slot": {"date": date, "time": time}
        }
    except Exception as e:
        logger.error(f"[create_appointment] Erro: {e}")
        return {
            "success": False,
            "message": f"{date} às {time}: Erro ao agendar - {e}",
            "slot": {"date": date, "time": time}
        }


def cancel_appointment(args, is_admin):
    professional_name = args.get("professional_name")
    procedure = args.get("procedure")
    user_phone = args.get("user_phone")
    professional_calendar_id = args.get("professional_calendar_id")
    date = args.get("date")
    time = args.get("time")

    service = get_calendar_service()
    timezone = pytz.timezone("America/Sao_Paulo")

    try:
        event_to_cancel = find_event(service, professional_calendar_id, date, time, timezone, procedure)
        if not event_to_cancel:
            return {
                "success": False,
                "message": f"Não encontrei um agendamento para {professional_name} em {date} às {time}. Verifique se os dados estão corretos.",
                "slot": {"date": date, "time": time}
            }

        if user_phone and 'extendedProperties' in event_to_cancel and 'private' in event_to_cancel[
            'extendedProperties']:
            event_user_phone = event_to_cancel['extendedProperties']['private'].get('user_phone')
            if event_user_phone and event_user_phone != user_phone and not is_admin:
                return {
                    "success": False,
                    "message": "Desculpe, somente a pessoa que fez o agendamento pode cancelá-lo.",
                    "slot": {"date": date, "time": time}
                }

        event_id = event_to_cancel['id']
        service.events().delete(calendarId=professional_calendar_id, eventId=event_id).execute()
        return {
            "success": True,
            "message": f"O agendamento com {professional_name} em {date} às {time} foi cancelado com sucesso.",
            "slot": {"date": date, "time": time}
        }

    except Exception as e:
        logger.error(f"[cancel_appointment] Erro: {e}")
        return {
            "success": False,
            "message": f"Erro ao cancelar agendamento: {e}",
            "slot": {"date": date, "time": time}
        }


def reschedule_appointment(args, is_admin):
    professional_name = args.get("professional_name")
    user_phone = args.get("user_phone")
    professional_calendar_id = args.get("professional_calendar_id")
    current_date = args.get("current_date")
    current_time = args.get("current_time")
    procedure = args.get("procedure")
    new_date = args.get("new_date")
    new_time = args.get("new_time")

    service = get_calendar_service()
    timezone = pytz.timezone("America/Sao_Paulo")

    try:
        current_event = find_event(service, professional_calendar_id, current_date, current_time, timezone, procedure)
        if not current_event:
            return {
                "success": False,
                "message": f"Não encontrei um agendamento para {professional_name} em {current_date} às {current_time}.",
                "slot": {
                    "from": {"date": current_date, "time": current_time},
                    "to": {"date": new_date, "time": new_time}
                }
            }

        if user_phone and 'extendedProperties' in current_event and 'private' in current_event['extendedProperties']:
            event_user_phone = current_event['extendedProperties']['private'].get('user_phone')
            if event_user_phone and event_user_phone != user_phone and not is_admin:
                return {
                    "success": False,
                    "message": "Desculpe, somente a pessoa que fez o agendamento pode reagendá-lo.",
                    "slot": {
                        "from": {"date": current_date, "time": current_time},
                        "to": {"date": new_date, "time": new_time}
                    }
                }

        self_attendance_procedure = current_event['extendedProperties']['private'].get('self_attendance_procedure',
                                                                                       "false").lower() == 'true'
        procedure_capacity = int(
            current_event['extendedProperties']['private'].get('procedure_capacity', DEFAULT_PROCEDURE_CAPACITY))

        new_start_local = parse_datetime(new_date, new_time, timezone)
        new_end_local = new_start_local + timedelta(minutes=get_event_duration(current_event))

        start_utc, end_utc = get_day_time_range(new_start_local.date(), timezone)
        events = service.events().list(
            calendarId=professional_calendar_id,
            timeMin=start_utc.isoformat(),
            timeMax=end_utc.isoformat(),
            singleEvents=True,
            orderBy="startTime"
        ).execute().get("items", [])

        is_available, reason = is_slot_available(
            new_start_local,
            new_end_local,
            events,
            timezone,
            user_phone,
            procedure,
            self_attendance_procedure,
            procedure_capacity
        )
        if not is_available:
            return {
                "success": False,
                "message": f"O novo horário ({new_date} às {new_time}) não está disponível. Motivo: {reason}. Escolha outro horário.",
                "slot": {
                    "from": {"date": current_date, "time": current_time},
                    "to": {"date": new_date, "time": new_time}
                }
            }

        current_event['start']['dateTime'] = new_start_local.astimezone(tz.utc).isoformat()
        current_event['end']['dateTime'] = new_end_local.astimezone(tz.utc).isoformat()
        current_event['start']['timeZone'] = 'UTC'
        current_event['end']['timeZone'] = 'UTC'

        service.events().update(calendarId=professional_calendar_id, eventId=current_event['id'],
                                body=current_event).execute()
        return {
            "success": True,
            "message": f"Reagendamento realizado com sucesso para {new_date} às {new_time}.",
            "slot": {
                "from": {"date": current_date, "time": current_time},
                "to": {"date": new_date, "time": new_time}
            }
        }

    except Exception as e:
        logger.error(f"[reschedule_appointment] Erro: {e}")
        return {
            "success": False,
            "message": f"Erro ao reagendar: {e}",
            "slot": {
                "from": {"date": current_date, "time": current_time},
                "to": {"date": new_date, "time": new_time}
            }
        }


def get_appointments(args):
    professional_name = args.get("professional_name")
    user_phone = args.get("user_phone")
    range_days = int(args.get("range_days", 15))
    professional_calendar_id = args.get("professional_calendar_id")

    service = get_calendar_service()
    timezone = pytz.timezone('America/Sao_Paulo')

    try:
        today = datetime.now(timezone).date()
        end_date = today + timedelta(days=range_days)

        start_utc = timezone.localize(datetime.combine(today, datetime.min.time())).astimezone(tz.utc)
        end_utc = timezone.localize(datetime.combine(end_date, datetime.max.time())).astimezone(tz.utc)

        events_result = service.events().list(
            calendarId=professional_calendar_id,
            timeMin=start_utc.isoformat(),
            timeMax=end_utc.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        user_appointments = []
        for event in events:
            props = event.get('extendedProperties', {}).get('private', {})
            if not user_phone or props.get('user_phone') == user_phone:
                start_time = event['start'].get('dateTime')
                if not start_time:
                    continue
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                local_dt = start_dt.astimezone(timezone)
                formatted_date = local_dt.strftime(INTERNAL_DATE_FORMAT)
                formatted_time = local_dt.strftime(INTERNAL_TIME_FORMAT)
                appointment_info = {
                    'professional': props.get('professional', professional_name),
                    'procedure': props.get('procedure', event.get('summary', 'Agendamento')),
                    'date': formatted_date,
                    'time': formatted_time,
                    'event_id': event['id']
                }
                user_appointments.append(appointment_info)

        user_appointments.sort(key=lambda x: (x['date'], x['time']))

        if not user_appointments:
            return {
                "success": False,
                "message": "O usuário não tem agendamentos para os próximos 15 dias."
            }
        user_resp = "do usuário" if user_phone else ""
        response = f"Próximos agendamentos {user_resp} nos próximos 15 dias:\n\n"
        for appt in user_appointments:
            response += f"📅 {appt['date']} às {appt['time']} - {appt['procedure']} com {appt['professional']}\n"

        return {
            "success": True,
            "message": f"{response}",
        }

    except Exception as e:
        logger.error(f"[get_user_appointments] Erro: {e}")
        return {
            "success": False,
            "message": f"Erro ao buscar agendamentos: {e}",
        }


def create_appointments(args):
    slots = args.get("slots", [])
    results = []

    for slot in slots:
        slot_args = {**args, **slot}
        result = create_appointment(slot_args)
        results.append(result)

    successes = [r for r in results if r["success"]]
    errors = [r for r in results if not r["success"]]

    if not errors:
        return json_success(results)
    elif not successes:
        return json_error(results)
    else:
        return json_partial_success(results)


def check_availabilities(args):
    slots = args.get("slots", [])
    results = []

    for slot in slots:
        slot_args = {**args, **slot}
        result = check_availability(slot_args)
        results.append(result)

    successes = [r for r in results if r["success"]]
    errors = [r for r in results if not r["success"]]

    if not errors:
        return json_success(results)
    elif not successes:
        return json_error(results)
    else:
        return json_partial_success(results)


def cancel_appointments(args, is_admin=False):
    slots = args.get("slots", [])
    results = []

    for slot in slots:
        slot_args = {**args, **slot}
        result = cancel_appointment(slot_args, is_admin)
        results.append(result)

    successes = [r for r in results if r["success"]]
    errors = [r for r in results if not r["success"]]

    if not errors:
        return json_success(results)
    elif not successes:
        return json_error(results)
    else:
        return json_partial_success(results)


def reschedule_appointments(args, is_admin=False):
    slots = args.get("slots", [])
    results = []

    for slot in slots:
        slot_args = {**args, **slot}
        result = reschedule_appointment(slot_args, is_admin)
        results.append(result)

    successes = [r for r in results if r["success"]]
    errors = [r for r in results if not r["success"]]

    if not errors:
        return json_success(results)
    elif not successes:
        return json_error(results)
    else:
        return json_partial_success(results)
