"""Tests de composition des messages d'alerte localises (FR / AR / EN)."""

from __future__ import annotations

from datetime import UTC, datetime

from src.notifications.messages import build_alert_message

_MOMENT = datetime(2026, 6, 29, 21, 0, 0, tzinfo=UTC)


def _build(language: str):
    return build_alert_message(
        language,
        rule="Temperature salle",
        sensor="el-haress-03-Sensor 16145",
        value="42.0 C",
        condition="GT",
        threshold=35.0,
        moment=_MOMENT,
    )


def test_message_localized_per_language() -> None:
    subject_fr, body_fr = _build("fr")
    subject_ar, body_ar = _build("ar")
    subject_en, body_en = _build("en")
    assert "ALERTE CRITIQUE" in subject_fr and "intervention immediate" in body_fr
    assert "تنبيه حرج" in subject_ar and "فوريا" in body_ar
    assert "CRITICAL ALERT" in subject_en and "immediate action" in body_en


def test_condition_rendered_as_symbol() -> None:
    _, body = _build("fr")
    assert "> 35.0" in body
    assert "GT" not in body


def test_unknown_language_falls_back_to_french() -> None:
    subject, _ = _build("xx")
    assert "ALERTE CRITIQUE" in subject
