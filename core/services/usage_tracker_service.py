from datetime import datetime

from core.dao.firebase_client import FirebaseClient


class UsageTrackerService:

    @staticmethod
    def update_token_usage(establishment_id: str, input_tokens: int, output_tokens: int):
        if not establishment_id:
            return

        month_key = datetime.now().strftime("%Y-%m")
        path = f"establishments/{establishment_id}/usage/{month_key}"

        existing = FirebaseClient.fetch_data(path) or {}

        updated = {
            "tokens_input": existing.get("tokens_input", 0) + input_tokens,
            "tokens_output": existing.get("tokens_output", 0) + output_tokens,
            "last_update": int(datetime.now().timestamp())
        }

        FirebaseClient.save_data(path, updated)
