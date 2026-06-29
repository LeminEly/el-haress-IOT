"""Envoi d'un message WhatsApp de test via Twilio (verification de configuration).

Le pipeline d'alerte utilise le meme provider ; ce script permet de valider la
configuration sans declencher de vraie alerte. Les identifiants viennent de la
configuration (.env), jamais d'un argument.

Usage (depuis backend/, .env renseigne) :
    python scripts/send_test_whatsapp.py --to +2224XXXXXXX [--message "..."]
"""

from __future__ import annotations

import argparse
import asyncio

from src.config import get_settings
from src.notifications.providers import CHANNEL_WHATSAPP, TwilioProvider


async def _send(to: str, message: str) -> None:
    settings = get_settings()
    provider = TwilioProvider(
        settings,
        channel=CHANNEL_WHATSAPP,
        sender=settings.twilio_whatsapp_from,
        prefix="whatsapp:",
    )
    if not provider.configured:
        raise SystemExit(
            "Twilio WhatsApp non configure. Renseigner dans .env : "
            "TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM."
        )
    await provider.send(recipient=to, subject="El-Haress", body=message)
    print(f"Message WhatsApp envoye a {to}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Envoi WhatsApp de test (Twilio)")
    parser.add_argument(
        "--to", required=True, help="destinataire au format international (ex. +2224XXXXXXX)"
    )
    parser.add_argument(
        "--message", default="Test de notification El-Haress.", help="contenu du message"
    )
    args = parser.parse_args()
    asyncio.run(_send(args.to, args.message))


if __name__ == "__main__":
    main()
