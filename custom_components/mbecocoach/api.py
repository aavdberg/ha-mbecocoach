"""Client for the observed Eco Coach personal statistics endpoint."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, tzinfo
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


@dataclass(frozen=True)
class PeriodStatistics:
    """Numeric summary from one captured statistics/all period."""

    drive_score: float | None
    consumption: float | None
    points: float | None


@dataclass(frozen=True)
class EcoCoachData:
    """Only summary metrics; no trip, message, or account details."""

    personal: PersonalStatistics
    daily: PeriodStatistics
    weekly: PeriodStatistics
    monthly: PeriodStatistics


def _number(value: Any, field: str) -> float | None:
    """Validate API numbers, excluding booleans and non-finite values."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise EcoCoachError(f"Statistics field {field} is not numeric")
    return float(value)


def parse_statistics(payload: Any) -> PersonalStatistics:
    """Extract metrics by the captured icon and unit, not localized labels."""
    if not isinstance(payload, dict):
        raise EcoCoachError("Personal statistics response is not an object")

    cards = payload.get("topCards")
    if not isinstance(cards, list):
        raise EcoCoachError("Personal statistics response has no top cards")

    metrics = {
        ("DRIVING", "PERCENT"): "drive_score",
        ("CONSUMPTION_ELECTRIC", "KWH100KM"): "avg_consumption",
        ("CO2", "KG"): "saved_emissions",
    }
    values: dict[str, float | None] = {}
    for card in cards:
        if not isinstance(card, dict):
            raise EcoCoachError("Personal statistics contains an invalid card")
        top = card.get("entryTop")
        if not isinstance(top, dict):
            continue
        quantity = top.get("value")
        if not isinstance(quantity, dict):
            continue
        field = metrics.get((card.get("icon"), quantity.get("unit")))
        if field is None:
            continue
        if field in values:
            raise EcoCoachError(f"Personal statistics contains duplicate {field} cards")
        value = quantity.get("value")
        values[field] = _number(value, field)
    if not values:
        raise EcoCoachError("Personal statistics response contains no supported metrics")
    return PersonalStatistics(values.get("drive_score"), values.get("avg_consumption"), values.get("saved_emissions"))


def parse_period_statistics(payload: Any) -> tuple[PeriodStatistics, PeriodStatistics, PeriodStatistics]:
    """Extract captured daily, weekly, and monthly aggregate metrics."""
    if not isinstance(payload, dict):
        raise EcoCoachError("Period statistics response is not an object")

    def period(name: str) -> PeriodStatistics:
        data = payload.get(name)
        if not isinstance(data, dict):
            raise EcoCoachError(f"Period statistics response has no {name}")

        def nested(*keys: str) -> Any:
            value: Any = data
            for key in keys:
                if value is None:
                    return None
                if not isinstance(value, dict):
                    raise EcoCoachError(f"Period statistics {name} contains an invalid {'/'.join(keys)}")
                value = value.get(key)
            return value

        consumption = nested("consumptionStatistics", "electricConsumption")
        if consumption is not None:
            if not isinstance(consumption, dict):
                raise EcoCoachError(f"Period statistics {name} has an invalid consumption value")
            if consumption.get("unit") != "KWH100KM":
                consumption = None
        return PeriodStatistics(
            _number(nested("driveScoreStatistics", "driveScore"), f"{name}.driveScore"),
            _number(consumption.get("value"), f"{name}.electricConsumption") if consumption else None,
            _number(nested("pointsSummary", "sum", "points"), f"{name}.points"),
        )

    return (period("dailyStatistics"), period("weeklyStatistics"), period("monthlyStatistics"))


def statistics_period(today: date, timezone: tzinfo) -> dict[str, str]:
    """Use two local Monday-Sunday calendar weeks as observed in the app."""

    def boundary(day: date, end: bool = False) -> str:
        local = datetime.combine(day, datetime.max.time() if end else datetime.min.time(), tzinfo=timezone)
        if end:
            local = local.replace(microsecond=0)
        return local.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    monday = today - timedelta(days=today.weekday())
    return {
        "from": boundary(monday),
        "to": boundary(monday + timedelta(days=6), end=True),
        "compareFrom": boundary(monday - timedelta(days=7)),
        "compareTo": boundary(monday - timedelta(days=1), end=True),
    }


class EcoCoachClient:
    """Access captured statistics endpoints using an existing bearer token."""

    def __init__(self, session: ClientSession, token: str, timezone: tzinfo = UTC) -> None:
        """Initialize the API client."""
        self._session = session
        self._token = token
        self._timezone = timezone

    async def async_personal_statistics(self, vin: str) -> PersonalStatistics:
        """Fetch personal statistics for one vehicle."""
        url = f"{BASE_URL}/api/v5/{vin}/statistics/personal"
        payload = await self._async_get(url, statistics_period(datetime.now(self._timezone).date(), self._timezone))
        return parse_statistics(payload)

    async def async_period_statistics(self, vin: str) -> tuple[PeriodStatistics, PeriodStatistics, PeriodStatistics]:
        """Fetch daily, weekly, and monthly summaries from the captured route."""
        payload = await self._async_get(f"{BASE_URL}/api/v5/{vin}/statistics/all")
        return parse_period_statistics(payload)

    async def _async_get(self, url: str, params: dict[str, str] | None = None) -> Any:
        """Request an Eco Coach endpoint and handle documented HTTP failures."""
        try:
            async with self._session.get(
                url,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "ecocoach-app-version": "5.7.0",
                    "ecocoach-platform": "iOS",
                },
                params=params,
                timeout=15,
            ) as response:
                if response.status in (401, 403):
                    raise EcoCoachAuthError("Eco Coach rejected the token")
                if response.status == 429:
                    raise EcoCoachRateLimitError("Eco Coach rate limit reached")
                if response.status != 200:
                    raise EcoCoachError(f"Statistics request failed (HTTP {response.status})")
                try:
                    payload = await response.json()
                except (ValueError, ClientError) as err:
                    raise EcoCoachError("Statistics response is not valid JSON") from err
        except (TimeoutError, ClientError) as err:
            raise EcoCoachConnectionError("Could not reach the Eco Coach statistics host") from err
        return payload
