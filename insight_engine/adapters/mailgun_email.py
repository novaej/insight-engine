import logging

import requests

logger = logging.getLogger(__name__)


class MailgunEmailProvider:
    def __init__(self, api_key: str, domain: str, from_email: str):
        self._api_key = api_key
        self._domain = domain
        self._from_email = from_email

    def send(self, to: str, subject: str, text: str, html: str | None = None) -> bool:
        """Send an email via Mailgun. Returns False (and logs) on any failure."""
        if not (self._api_key and self._domain and self._from_email):
            logger.warning("Mailgun not configured; skipping email to %s", to)
            return False

        data = {
            "from": self._from_email,
            "to": to,
            "subject": subject,
            "text": text,
        }
        if html:
            data["html"] = html

        try:
            response = requests.post(
                f"https://api.mailgun.net/v3/{self._domain}/messages",
                auth=("api", self._api_key),
                data=data,
                timeout=10,
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error("Mailgun send failed for %s: %s", to, e)
            return False
