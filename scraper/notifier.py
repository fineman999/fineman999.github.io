import json
import os
import requests
import google.auth.transport.requests
from google.oauth2 import service_account


class FCMNotifier:
    FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"

    def __init__(self, project_id: str = None, credentials=None):
        self.project_id = project_id or os.environ["FCM_PROJECT_ID"]
        if credentials:
            self.credentials = credentials
        else:
            service_account_info = json.loads(os.environ["FCM_SERVICE_ACCOUNT_JSON"])
            self.credentials = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=[self.FCM_SCOPE]
            )

    def _get_access_token(self) -> str:
        req = google.auth.transport.requests.Request()
        self.credentials.refresh(req)
        return self.credentials.token

    def send_one(self, token: str, title: str, body: str, link: str) -> dict:
        url = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"
        payload = {
            "message": {
                "token": token,
                "notification": {"title": title, "body": body},
                "webpush": {
                    "fcm_options": {"link": link}
                }
            }
        }
        headers = {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json"
        }
        res = requests.post(url, json=payload, headers=headers)
        if res.status_code == 200:
            return {"status": "sent"}
        else:
            error = res.json().get("error", {}).get("message", str(res.text))
            return {"status": "failed", "error_msg": error}

    def send_batch(self, notifications: list[dict]) -> list[dict]:
        """notifications: [{"token": ..., "title": ..., "body": ..., "link": ...}]"""
        return [self.send_one(**n) for n in notifications]
