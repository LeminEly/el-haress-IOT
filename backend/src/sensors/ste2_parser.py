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
# Unite STE2 -> type de capteur. Table extensible : ajouter un code suffit pour
# prendre en charge un nouveau type, sans toucher au reste du collector.
_UNIT_TO_KIND = {
    "C": "temperature",
    "F": "temperature",
    "%": "humidity",
    "WLD": "flood",
}
# Types a etat binaire (detecte / normal) plutot qu'a valeur continue.
_BINARY_KINDS = frozenset({"flood", "contact", "motion", "smoke"})


@dataclass(frozen=True)
class Ste2Sample:
    gateway_ref: str
    name: str
    unit: str | None
    kind: str
    value: float | None
    valid: bool
    # Codes d'etat appareil (status/state, status/alarm). Pour un capteur binaire,
    # l'etat declenche sort la valeur de la plage (sentinelle -999.9) : on s'appuie
    # alors sur status_state (1=normal, 2=alarme) plutot que sur la valeur continue.
    status_state: str = "1"
    alarm: str = "0"
    hardware_id: str | None = None


def infer_kind(unit: str | None) -> str:
    if unit is None:
        return "unknown"
    return _UNIT_TO_KIND.get(unit.strip(), "unknown")


def is_binary_kind(kind: str) -> bool:
    """Un capteur binaire n'a pas de mesure continue : on en derive un etat 0/1."""
    return kind in _BINARY_KINDS


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
        alarm = _nested_text(entry, "status", "alarm")
        status_state = _nested_text(entry, "status", "state") or state
        kind = infer_kind(unit)
        try:
            raw_value: float | None = float(fields.get("Value", ""))
        except ValueError:
            raw_value = None
        valid = (
            raw_value is not None
            and abs(raw_value - _INVALID_VALUE) > 1e-6
            and state == "1"
            and unit is not None
        )
        if not valid:
            value: float | None = None
        elif is_binary_kind(kind):
            # Capteur binaire : on derive un etat 0/1. "Detecte" si l'appareil
            # signale une alarme ou si la valeur brute est non nulle.
            detected = alarm == "1" or (raw_value is not None and raw_value != 0.0)
            value = 1.0 if detected else 0.0
        else:
            value = raw_value
        samples.append(
            Ste2Sample(
                gateway_ref=gateway_ref,
                name=fields.get("Name", ""),
                unit=unit,
                kind=kind,
                value=value,
                valid=valid,
                status_state=status_state,
                alarm=alarm,
            )
        )
    return samples


def _nested_text(entry, parent: str, child: str) -> str:
    """Texte d'un sous-element (`<parent><child>...`), chaine vide si absent."""
    for element in entry:
        if _localname(element.tag) == parent:
            for sub in element:
                if _localname(sub.tag) == child:
                    return (sub.text or "").strip()
    return ""


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
