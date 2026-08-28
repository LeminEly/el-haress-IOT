"""Composition des messages d'alerte, localises (FR / AR / EN).

Le message est construit dans la langue du compte destinataire. Ton sobre et
factuel, sans emoji. Le canal (WhatsApp/SMS/Email) recoit le meme contenu.
"""

from __future__ import annotations

from datetime import datetime

_DEFAULT_LANGUAGE = "fr"

# Symbole lisible de la condition de seuil, independant de la langue.
_CONDITION_SYMBOL = {"GT": ">", "GTE": ">=", "LT": "<", "LTE": "<=", "EQ": "="}

_TEMPLATES: dict[str, dict[str, str]] = {
    "fr": {
        "subject": "ALERTE CRITIQUE - {rule}",
        "body": (
            "ALERTE CRITIQUE - intervention immediate requise.\n"
            "Capteur : {sensor}\n"
            "Mesure : {value} (seuil {condition} {threshold})\n"
            "Heure : {time} UTC"
        ),
    },
    "ar": {
        "subject": "تنبيه حرج - {rule}",
        "body": (
            "تنبيه حرج - يتطلب تدخلا فوريا.\n"
            "المستشعر: {sensor}\n"
            "القياس: {value} (العتبة {condition} {threshold})\n"
            "الوقت: {time} UTC"
        ),
    },
    "en": {
        "subject": "CRITICAL ALERT - {rule}",
        "body": (
            "CRITICAL ALERT - immediate action required.\n"
            "Sensor: {sensor}\n"
            "Reading: {value} (threshold {condition} {threshold})\n"
            "Time: {time} UTC"
        ),
    },
}


def build_alert_message(
    language: str,
    *,
    rule: str,
    sensor: str,
    value: str,
    condition: str,
    threshold: float,
    moment: datetime,
) -> tuple[str, str]:
    """Retourne (sujet, corps) localises pour une alerte critique."""
    template = _TEMPLATES.get(language, _TEMPLATES[_DEFAULT_LANGUAGE])
    fields = {
        "rule": rule,
        "sensor": sensor,
        "value": value,
        "condition": _CONDITION_SYMBOL.get(condition, condition),
        "threshold": threshold,
        "time": moment.strftime("%Y-%m-%d %H:%M:%S"),
    }
    return template["subject"].format(**fields), template["body"].format(**fields)
