"""Client HTTP de la passerelle STE2 LITE (lecture seule).

Interroge `GET /values.xml` (valeurs courantes) et, en best-effort, `GET /` pour
resoudre l'identite materielle (SenId). N'ecrit jamais la configuration de
l'appareil. Timeout court ; les erreurs reseau remontent au collector qui gere la
resilience.
"""

from __future__ import annotations

from typing import Protocol

import httpx

from .ste2_parser import Ste2Sample, merge_identities, parse_identities, parse_values


class SampleSource(Protocol):
    async def fetch_samples(self, base_url: str) -> list[Ste2Sample]: ...


class Ste2Client:
    def __init__(self, *, timeout: float = 5.0) -> None:
        self._timeout = timeout

    async def fetch_samples(self, base_url: str) -> list[Ste2Sample]:
        root = base_url.rstrip("/")
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            values_response = await client.get(f"{root}/values.xml")
            values_response.raise_for_status()
            samples = parse_values(values_response.text)

            identities: dict[str, str] = {}
            try:
                config_response = await client.get(f"{root}/")
                config_response.raise_for_status()
                identities = parse_identities(config_response.text)
            except httpx.HTTPError:
                identities = {}

        return merge_identities(samples, identities)
