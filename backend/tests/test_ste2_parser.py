"""Tests du parsing values.xml : mapping dynamique des types et capteurs binaires.

Echantillons calques sur l'unite reellement deployee (voir docs/sensor-system-ste2).
"""

from __future__ import annotations

from src.sensors.ste2_parser import infer_kind, is_binary_kind, parse_values

_NS = 'xmlns:val="http://www.hw-group.com/XMLSchema/ste/values.xsd"'


def _xml(*entries: str) -> str:
    return f"<val:Root {_NS}><SenSet>{''.join(entries)}</SenSet></val:Root>"


def _entry(ref: str, name: str, units: str, value: str, state: str, alarm: str) -> str:
    return (
        f"<Entry><ID>{ref}</ID><Name>{name}</Name><Units>{units}</Units>"
        f"<Value>{value}</Value><State>{state}</State>"
        f"<status><state>{state}</state><alarm>{alarm}</alarm></status></Entry>"
    )


def test_temperature_is_continuous() -> None:
    (sample,) = parse_values(_xml(_entry("16145", "Temp", "C", "30.5", "1", "0")))
    assert sample.kind == "temperature"
    assert is_binary_kind(sample.kind) is False
    assert sample.valid is True
    assert sample.value == 30.5


def test_flood_unit_maps_to_binary_kind() -> None:
    # Unite WLD -> type flood (binaire). Auparavant non reconnu (kind unknown).
    (sample,) = parse_values(_xml(_entry("12571", "Flood", "WLD", "0", "1", "0")))
    assert sample.kind == "flood"
    assert is_binary_kind(sample.kind) is True
    assert sample.valid is True


def test_binary_value_normal_when_no_alarm() -> None:
    # Flood sans alarme et valeur 0 -> etat 0.0 (Normal).
    (sample,) = parse_values(_xml(_entry("12571", "Flood", "WLD", "0", "1", "0")))
    assert sample.value == 0.0


def test_binary_value_detected_on_alarm() -> None:
    # L'alarme appareil -> etat 1.0 (Detecte), meme si Value reste 0.
    (sample,) = parse_values(_xml(_entry("12571", "Flood", "WLD", "0", "1", "1")))
    assert sample.value == 1.0


def test_invalid_when_state_zero_or_sentinel() -> None:
    invalid_state = parse_values(_xml(_entry("6686", "S", "C", "20.0", "0", "0")))[0]
    sentinel = parse_values(_xml(_entry("6686", "S", "C", "-999.9", "1", "0")))[0]
    assert invalid_state.valid is False
    assert sentinel.valid is False
    assert invalid_state.value is None


def test_infer_kind_unknown_for_unmapped_unit() -> None:
    assert infer_kind(None) == "unknown"
    assert infer_kind("XYZ") == "unknown"
