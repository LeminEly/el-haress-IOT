"""Normalisation des numeros de telephone au format international (E.164).

Le numero est l'identifiant de connexion ; il doit etre stocke sous une forme
canonique unique. Un numero deja prefixe par `+` est interprete a l'international,
sinon la region par defaut (config) s'applique.
"""

from __future__ import annotations

import phonenumbers


def normalize_phone(raw: str, *, default_region: str) -> str | None:
    """Retourne le numero au format E.164, ou None s'il est invalide."""
    candidate = raw.strip()
    region = None if candidate.startswith("+") else default_region
    try:
        parsed = phonenumbers.parse(candidate, region)
    except phonenumbers.NumberParseException:
        return None
    if not phonenumbers.is_valid_number(parsed):
        return None
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
