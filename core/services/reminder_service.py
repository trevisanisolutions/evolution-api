import logging
from datetime import datetime, timedelta

from core.dao.firebase_client import FirebaseClient
from core.services.calendar.client import get_calendar_service
from core.services.whatsapp_service import WhatsappService
from core.utils.constants import TIMEZONE, TODAY

logger = logging.getLogger(__name__)


class ReminderService:

    @staticmethod
    def run():
        logger.info("[Reminder] Executando rotina de envio de lembretes de 24h...")

        establishments = FirebaseClient.fetch_data("establishments") or {}
        target_date = TODAY + timedelta(days=1)
        logger.info(f"[Reminder] Data dos eventos:{target_date}")

        calendar_service = get_calendar_service()

        for establishments_phone, establishment_data in establishments.items():
            if not establishment_data.get("config", {}).get("calendars"):
                logger.warning(f"[Reminder] Estabelecimento {establishments_phone} não possui calendários configurados.")
                continue

            instance_name = establishment_data.get("config", {}).get("instance_name")
            if not instance_name:
                logger.warning(f"[Reminder] Estabelecimento {establishments_phone} não possui nome de instância configurado.")
                continue

            events_user_map = {}

            for calendar_id in establishment_data.get("config", {}).get("calendars", []):
                try:
                    start_dt = TIMEZONE.localize(datetime.combine(target_date, datetime.min.time()))
                    end_dt = TIMEZONE.localize(datetime.combine(target_date, datetime.max.time()))

                    events_result = calendar_service.events().list(
                        calendarId=calendar_id,
                        timeMin=start_dt.isoformat(),
                        timeMax=end_dt.isoformat(),
                        singleEvents=True,
                        orderBy='startTime'
                    ).execute()

                    for event in events_result.get("items", []):
                        props = event.get("extendedProperties", {}).get("private", {})
                        if props.get("created_by") != "virtual_assistant":
                            logger.warning(f"[Reminder] Evento {event['id']} não foi criado pelo assistente virtual, ignorando.")
                            continue
                        if props.get("reminder_24h_sent"):
                            logger.warning(f"[Reminder] Evento {event['id']} já teve lembrete enviado ou não foi criado pelo assistente virtual, ignorando.")
                            continue

                        user_phone = props.get("user_phone")
                        if not user_phone:
                            logger.warning(f"[Reminder] Evento {event['id']} não possui telefone do usuário, ignorando.")
                            continue

                        start_time = event["start"].get("dateTime")
                        if not start_time:
                            logger.warning(f"[Reminder] Evento {event['id']} não possui horário de início, ignorando.")
                            continue

                        dt = datetime.fromisoformat(start_time.replace("Z", "+00:00")).astimezone(TIMEZONE)
                        hour_str = dt.strftime("%H:%M")

                        entry = {
                            "time": hour_str,
                            "procedure": props.get("procedure", "Agendamento"),
                            "professional": props.get("professional", "Profissional"),
                            "calendar_id": calendar_id,
                            "user_name": props.get("user_name", "Cliente"),
                            "event": event,
                            "instance": instance_name
                        }
                        logger.info(f"[Reminder] Evento encontrado para {user_phone}: {entry}")

                        events_user_map.setdefault(user_phone, []).append(entry)

                except Exception as e:
                    logger.error(f"[Reminder] Erro ao processar calendário {calendar_id}: {e}")

            for user_phone, events in events_user_map.items():
                try:
                    user_name = events[0].get("user_name")
                    lines = [f"Olá {user_name}! Você tem os seguintes agendamentos amanhã:\n"]
                    for e in sorted(events, key=lambda x: x["time"]):
                        lines.append(f"- {e['time']} - {e['procedure']} com {e['professional']}")
                    lines.append(
                        "\nAté lá! 😊\nCaso não possa comparecer, por favor, reagende ou cancele o agendamento com antecedência.")

                    message = "\n".join(lines)
                    WhatsappService.send_evolution_response(events[0]["instance"], user_phone, message)

                    for e in events:
                        e["event"].setdefault("extendedProperties", {}).setdefault("private", {})[
                            "reminder_24h_sent"] = datetime.now(TIMEZONE).isoformat()
                        calendar_service.events().update(
                            calendarId=e["calendar_id"],
                            eventId=e["event"]["id"],
                            body=e["event"]
                        ).execute()

                    logger.info(f"[Reminder] Lembrete enviado para {user_phone}, ({len(events)} eventos)")

                except Exception as e:
                    logger.error(f"[Reminder] Erro ao enviar lembrete para {user_phone}: {e}")

        logger.info("[Reminder] Finalizado.")
