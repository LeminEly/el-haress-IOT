"""Providers de notification : WhatsApp et SMS (Twilio), Email (SMTP).

Tous les secrets viennent de la configuration (variables d'environnement). Un
provider non configure se signale et ne fait rien (pas d'echec bloquant). Les
canaux sont identifies par des chaines (`whatsapp`, `sms`, `email`) pour eviter un
couplage avec le module alerting.
"""

from __future__ import annotations

from email.message import EmailMessage

import aiosmtplib
import httpx
import structlog

from ..config import Settings

logger = structlog.get_logger(__name__)

CHANNEL_WHATSAPP = "whatsapp"
CHANNEL_SMS = "sms"
CHANNEL_EMAIL = "email"

_TWILIO_URL = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


class TwilioProvider:
    """WhatsApp ou SMS via l'API REST Twilio (sans SDK, httpx async)."""

    def __init__(self, settings: Settings, *, channel: str, sender: str, prefix: str) -> None:
        self.channel = channel
        self._settings = settings
        self._sender = sender
        self._prefix = prefix

    @property
    def configured(self) -> bool:
        return bool(
            self._settings.twilio_account_sid and self._settings.twilio_auth_token and self._sender
        )

    async def send(self, *, recipient: str, subject: str, body: str) -> None:
        if not self.configured:
            logger.warning("notification_provider_unconfigured", channel=self.channel)
            return
        url = _TWILIO_URL.format(sid=self._settings.twilio_account_sid)
        data = {
            "From": f"{self._prefix}{self._sender}",
            "To": f"{self._prefix}{recipient}",
            "Body": f"{subject}\n{body}",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                data=data,
                auth=(self._settings.twilio_account_sid, self._settings.twilio_auth_token),
            )
            response.raise_for_status()


class EmailProvider:
    channel = CHANNEL_EMAIL

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def configured(self) -> bool:
        return bool(self._settings.smtp_host and self._settings.smtp_from)

    async def send(self, *, recipient: str, subject: str, body: str) -> None:
        if not self.configured:
            logger.warning("notification_provider_unconfigured", channel=self.channel)
            return
        message = EmailMessage()
        message["From"] = self._settings.smtp_from
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        await aiosmtplib.send(
            message,
            hostname=self._settings.smtp_host,
            port=self._settings.smtp_port,
            username=self._settings.smtp_user or None,
            password=self._settings.smtp_password or None,
            start_tls=self._settings.smtp_port == 587,
        )
