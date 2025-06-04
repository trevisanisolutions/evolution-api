# dto/presence_update_dto.py

class PresenceUpdateDTO:
    def __init__(self, payload: dict):
        self.event = payload.get("event")
        self.presences = payload.get("data", {}).get("presences", {})
        self.instance_name = payload.get("instance", "")

        if not isinstance(self.presences, dict):
            raise ValueError("Formato inválido para 'presences'")

    def get_user_presence_info(self):
        if not self.presences:
            raise ValueError("Presences ausente")

        remote_jid, presence_data = next(iter(self.presences.items()))
        user_phone = remote_jid.split("@")[0]
        last_presence = presence_data.get("lastKnownPresence")

        return user_phone, last_presence
