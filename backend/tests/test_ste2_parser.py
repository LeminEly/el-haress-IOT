"""Tests du parsing values.xml : mapping dynamique des types et valeur brute.

Echantillons calques sur l'unite reellement deployee (voir docs/sensor-system-ste2).
La valeur est TOUJOURS celle renvoyee par le STE2, sans reinterpretation.
"""

from __future__ import annotations

from src.sensors.ste2_parser import infer_kind, parse_values

_NS = 'xmlns:val="http://www.hw-group.com/XMLSchema/ste/values.xsd"'


def _xml(*entries: str) -> str:
    return f"<val:Root {_NS}><SenSet>{''.join(entries)}</SenSet></val:Root>"


def _entry(ref: str, name: str, units: str, value: str, state: str) -> str:
    return (
        f"<Entry><ID>{ref}</ID><Name>{name}</Name><Units>{units}</Units>"
        f"<Value>{value}</Value><State>{state}</State>"
        f"<status><state>{state}</state><alarm>0</alarm></status></Entry>"
    )


def test_kind_inferred_from_unit() -> None:
    temp = parse_values(_xml(_entry("16145", "Temp", "C", "30.5", "1")))[0]
    flood = parse_values(_xml(_entry("12571", "Flood", "WLD", "0", "1")))[0]
    assert temp.kind == "temperature"
    assert flood.kind == "flood"


def test_value_is_raw_never_reinterpreted() -> None:
    # La valeur stockee est exactement celle du STE2 : mesure continue pour une
    # temperature, etat brut pour un flood (0 sec, 1 mouille, 2/3 autres etats...).
    temp = parse_values(_xml(_entry("16145", "Temp", "C", "30.5", "1")))[0]
    assert temp.value == 30.5

    dry = parse_values(_xml(_entry("12571", "Flood", "WLD", "0", "1")))[0]
    assert dry.value == 0.0

    wet = parse_values(_xml(_entry("12571", "Flood", "WLD", "1", "5")))[0]
    assert wet.value == 1.0

    multi = parse_values(_xml(_entry("999", "Etat", "X", "2", "1")))[0]
    assert multi.value == 2.0  # etat 2 conserve, pas ecrase en 0/1


def test_alarm_state_stays_valid() -> None:
    # State=5 = lecture valide EN ALARME (hors plage), pas une deconnexion. Un flood
    # mouille (Value=1, State=5) ou une temperature hors seuil ne doit pas disparaitre.
    # Regression : le parser rejetait tout State != 1.
    flood = parse_values(_xml(_entry("12571", "Flood", "WLD", "1", "5")))[0]
    temp = parse_values(_xml(_entry("16145", "Temp", "C", "65.0", "5")))[0]
    assert flood.valid is True and flood.value == 1.0
    assert temp.valid is True and temp.value == 65.0


def test_invalid_when_state_zero_or_sentinel() -> None:
    invalid_state = parse_values(_xml(_entry("6686", "S", "C", "20.0", "0")))[0]
    sentinel = parse_values(_xml(_entry("6686", "S", "C", "-999.9", "1")))[0]
    assert invalid_state.valid is False
    assert sentinel.valid is False
    assert invalid_state.value is None


def test_infer_kind_unknown_for_unmapped_unit() -> None:
    assert infer_kind(None) == "unknown"
    assert infer_kind("XYZ") == "unknown"
