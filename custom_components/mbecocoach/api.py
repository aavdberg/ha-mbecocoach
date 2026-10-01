"""Client for the observed Eco Coach personal statistics endpoint."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from aiohttp import ClientError, ClientSession

from .const import BASE_URL


class EcoCoachError(Exception):
    """Eco Coach request or response failed."""


class EcoCoachAuthError(EcoCoachError):
    """The supplied token was rejected."""


class EcoCoachConnectionError(EcoCoachError):
    """The Eco Coach server could not be reached."""


class EcoCoachRateLimitError(EcoCoachError):
    """The server requested fewer calls."""


@dataclass(frozen=True)
class PersonalStatistics:
    """Fields confirmed in the observed personal statistics response."""

    drive_score: float | None
    avg_consumption: float | None
    saved_emissions: float | None


def parse_statistics(payload: Any) -> PersonalStatistics:
    """Validate supported numeric fields without guessing undocumented fields."""
    if not isinstance(payload, dict):
        raise EcoCoachError("Personal statistics response is not an object")

    fields = ("driveScore", "avgConsumption", "savedEmissions")
    if not any(field in payload for field in fields):
        raise EcoCoachError("Personal statistics response contains no supported metrics")

    values: list[float | None] = []
    for field in fields:
        value = payload.get(field)
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
        ):
            raise EcoCoachError(f"Personal statistics field {field} is not numeric")
        values.append(float(value) if value is not None else None)
    return PersonalStatistics(*values)


class EcoCoachClient:
    """Access only the captured endpoint; no unverified OAuth or API routes."""

    def __init__(self, session: ClientSession, token: str) -> None:
        """Initialize the API client."""
        self._session = session
        self._token = token

    async def async_personal_statistics(self, vin: str) -> PersonalStatistics:
        """Fetch personal statistics for one vehicle."""
        url = f"{BASE_URL}/api/v5/{vin}/statistics/personal"
        try:
            async with self._session.get(
                url,
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=15,
            ) as response:
                if response.status in (401, 403):
                    raise EcoCoachAuthError("Eco Coach rejected the token")
                if response.status == 429:
                    raise EcoCoachRateLimitError("Eco Coach rate limit reached")
                if response.status != 200:
                    raise EcoCoachError(f"Personal statistics request failed (HTTP {response.status})")
                try:
                    payload = await response.json()
                except (ValueError, ClientError) as err:
                    raise EcoCoachError("Personal statistics response is not valid JSON") from err
        except (TimeoutError, ClientError) as err:
            raise EcoCoachConnectionError("Could not reach the Eco Coach statistics host") from err
        return parse_statistics(payload)
