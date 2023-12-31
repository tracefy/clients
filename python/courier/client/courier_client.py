import base64
import json
import os
import requests
from dotenv import load_dotenv

from sentry_sdk import capture_exception

load_dotenv()


class CourierClient:
    storage_templates = "storage/templates.json"
    storage_fallback_templates = "storage/fallback-templates.json"

    def __init__(self):
        self.bearer_token = os.getenv("COURIER_BEARER_TOKEN")

        self.url = os.getenv("COURIER_URL", "https://api.courier.com/")
        if not self.url.endswith("/"):
            self.url = self.url + "/"
        try:
            self.templates = self._get_templates()
        except Exception as e:
            capture_exception(e)
            self.templates = self._get_fallback_templates()

    def _request(self, uri, method="GET"):
        try:
            response = requests.request(method, self.url + uri, headers=self._get_headers())
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            capture_exception(e)
        return None

    def _get_templates(self) -> list:
        if not os.path.isfile(self.storage_templates):
            response = self._request("notifications")

            templates = list()
            if response.get("results"):
                for item in response.get("results"):
                    templates.append(item.get("id"))
            if response.get("paging"):
                if response.get("paging").get("more"):
                    print("Template pagination is not implemented please implement this is needed for new templates.")

            f = open(self.storage_templates, "w")
            f.write(json.dumps(templates))
            f.close()
        else:
            f = open(self.storage_templates, 'r')
            templates = json.loads(f.read())
        return templates

    def update_fallback_templates(self):
        templates = self._get_templates()
        f = open(self.storage_fallback_templates, "w")
        f.write(json.dumps(templates))
        f.close()

    def _get_fallback_templates(self):
        f = open(self.storage_fallback_templates, 'r')
        templates = json.loads(f.read())
        f.close()
        return templates

    def _get_headers(self):
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f'Authorization: Bearer {self.bearer_token}'
        }

    def is_valid_template(self, template_id):
        return template_id in self.templates

    def send(self, email, template_id, data, attachment):
        payload = {
            "message": {
                "routing": {
                    "method": "single",
                    "channels": ["email"],
                },
                "template": template_id,
                "to": {
                    "email": email
                },
                "data": data,
            },
        }

        if attachment:
            content = base64.b64encode(bytes(attachment.get("content"), 'utf-8')).decode('utf-8')
            payload['message']['providers'] = {
                "smtp": {
                    "override": {
                        "body": {
                            "attachments": [
                                {
                                    "filename": attachment.get("file_name"),
                                    "content": content,
                                    "encoding": attachment.get("encoding")
                                }
                            ]
                        },
                    }
                }
            }
            payload['message']['channels'] = {
                "email": {
                    "override": {
                        "attachments": [
                            {
                                "filename": "report.csv",
                                "contentType": attachment.get("content_type"),
                                "data": content
                            }
                        ]
                    }
                }
            }
        return requests.request("POST", self.url + "send", json=payload, headers=self._get_headers())
