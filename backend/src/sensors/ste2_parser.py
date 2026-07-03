"""Parsing du XML de la passerelle STE2 LITE (fonctions pures, sans reseau).

Source potentiellement non fiable (appareil sur le LAN, sans auth) : on utilise
`defusedxml` et on borne/valide chaque champ. Regles d'invalidite (capteur muet /
non connecte) : `Value == -999.9`, ou `State != 1`, ou unite absente.
Voir docs/sensor-system-ste2.md.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from defusedxml.ElementTree import fromstring

_INVALID_VALUE = -999.9
# Unite STE2 -> categorie de capteur (pour l'affichage/groupement uniquement,
# jamais pour interpreter la valeur). Table extensible : ajouter un code suffit.
_UNIT_TO_KIND = {
    "C": "temperature",
    "F": "temperature",
    "%": "humidity",
    "WLD": "flood",
}


@dataclass(frozen=True)
class Ste2Sample:
    gateway_ref: str
    name: str
    unit: str | None
    kind: str
    # Valeur telle que renvoyee par le STE2, sans reinterpretation : un capteur
    # continu donne sa mesure, un capteur a etats discrets donne son etat brut
    # (0/1 pour un flood, 0/1/2/3 pour d'autres). On ne force jamais en binaire.
    value: float | None
    valid: bool
    hardware_id: str | None = None


def infer_kind(unit: str | None) -> str:
    if unit is None:
        return "unknown"
    return _UNIT_TO_KIND.get(unit.strip(), "unknown")


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _iter_named(root, name: str):
    return (element for element in root.iter() if _localname(element.tag) == name)


def parse_values(xml_text: str) -> list[Ste2Sample]:
    """Parse `values.xml` en echantillons. Une valeur invalide donne value=None."""
    root = fromstring(xml_text)
    samples: list[Ste2Sample] = []
    for entry in _iter_named(root, "Entry"):
        fields = {_localname(child.tag): (child.text or "").strip() for child in entry}
        gateway_ref = fields.get("ID", "")
        if not gateway_ref:
            continue
        unit = fields.get("Units") or None
        state = fields.get("State", "0")
        kind = infer_kind(unit)
        try:
            raw_value: float | None = float(fields.get("Value", ""))
        except ValueError:
            raw_value = None
        # State : 0 = pas de capteur / invalide ; 1 = normal ; >1 (ex. 5) = lecture
        # valide EN ALARME (hors plage). On accepte donc tout State != 0 : sinon un
        # capteur en alarme (flood mouille, temperature hors seuil) disparaitrait au
        # pire moment. Seul State == 0 (ou la sentinelle -999.9, ou l'unite absente)
        # signale reellement l'absence de mesure.
        valid = (
            raw_value is not None
            and abs(raw_value - _INVALID_VALUE) > 1e-6
            and state != "0"
            and unit is not None
        )
        # On stocke la valeur BRUTE du STE2, sans reinterpretation : le STE2 renvoie
        # deja l'etat pertinent (0/1 pour un flood, 0/1/2/3 pour d'autres, une mesure
        # continue sinon). Aucune valeur en dur, aucun forcage en binaire.
        samples.append(
            Ste2Sample(
                gateway_ref=gateway_ref,
                name=fields.get("Name", ""),
                unit=unit,
                kind=kind,
                value=raw_value if valid else None,
                valid=valid,
            )
        )
    return samples


def parse_identities(xml_text: str) -> dict[str, str]:
    """Mappe `gateway_ref` (ID passerelle) -> `SenId` (adresse 1-Wire), depuis `/`."""
    root = fromstring(xml_text)
    identities: dict[str, str] = {}
    for sensor in _iter_named(root, "sensor"):
        gateway_ref = sensor.get("id", "")
        sen_id = next(
            ((child.text or "").strip() for child in sensor if _localname(child.tag) == "SenId"),
            "",
        )
        if gateway_ref and sen_id:
            identities[gateway_ref] = sen_id
    return identities


def merge_identities(samples: list[Ste2Sample], identities: dict[str, str]) -> list[Ste2Sample]:
    return [replace(s, hardware_id=identities.get(s.gateway_ref)) for s in samples]
