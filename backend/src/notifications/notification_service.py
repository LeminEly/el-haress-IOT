"""Dispatcher de notifications multi-canal.

Route un message vers les canaux choisis par la regle. Un canal en echec n'empeche
pas les autres (chaque envoi est isole). Le destinataire vient du compte (telephone
pour WhatsApp/SMS, email pour Email) : aucun destinataire code en dur.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

import structlog

from ..config import Settings
from .providers import (
    CHANNEL_EMAIL,
    CHANNEL_SMS,
    CHANNEL_WHATSAPP,
    EmailProvider,
    TwilioProvider,
)

logger = structlog.get_logger(__name__)


class NotificationProvider(Protocol):
    channel: str

    async def send(self, *, recipient: str, subject: str, body: str) -> None: ...


class NotificationService:
    def __init__(self, providers: dict[str, NotificationProvider]) -> None:
        self._providers = providers

    @classmethod
    def from_settings(cls, settings: Settings) -> NotificationService:
        return cls(
            {
                CHANNEL_WHATSAPP: TwilioProvider(
                    settings,
                    channel=CHANNEL_WHATSAPP,
                    sender=settings.twilio_whatsapp_from,
                    prefix="whatsapp:",
                ),
                CHANNEL_SMS: TwilioProvider(
                    settings, channel=CHANNEL_SMS, sender=settings.twilio_sms_from, prefix=""
                ),
                CHANNEL_EMAIL: EmailProvider(settings),
            }
        )

    async def dispatch(
        self,
        *,
        channels: Iterable[str],
        phone: str | None,
        email: str | None,
        subject: str,
        body: str,
    ) -> None:
        for channel in channels:
            provider = self._providers.get(channel)
            recipient = email if channel == CHANNEL_EMAIL else phone
            if provider is None or not recipient:
                continue
            try:
                await provider.send(recipient=recipient, subject=subject, body=body)
            except Exception as exc:  # un canal en echec ne bloque pas les autres
                logger.error("notification_failed", channel=channel, error=str(exc))
