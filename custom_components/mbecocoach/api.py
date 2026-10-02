"""Client for the observed Eco Coach personal statistics endpoint."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, tzinfo
from typing import Any

from aiohttp import ClientError, ClientSession

from .const import BASE_URL

_LOGGER = logging.getLogger(__name__)


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
    points: float | None = None


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
    points: PointsSummary | None = None
    awards: tuple[PointsAward, ...] = ()


@dataclass(frozen=True)
class PointsSummary:
    """Account total and recent grouped points, without activity details."""

    total: int
    recent: dict[str, int]


@dataclass(frozen=True)
class PointsAward:
    """Minimal award metadata used only for new HA event history."""

    id: str
    category: str
    points: int
    occurred_at: datetime


_POINT_CATEGORIES = frozenset({"DRIVING", "CHARGING", "PARKING", "PERSONAL_CHALLENGE"})
_AWARD_CATEGORIES = {"DRIVE": "driving", "CHARGE": "charging", "PARK": "parking"}


def _points(value: Any) -> int:
    """Only whole, nonnegative point balances are supported."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise EcoCoachError("Points response contains invalid points")
    return value


def parse_points(payload: Any) -> PointsSummary:
    """Extract lifetime points and observed recent categories."""
    if not isinstance(payload, dict) or not isinstance(payload.get("latestGroupedPoints"), list):
        raise EcoCoachError("Points response is invalid")
    recent: dict[str, int] = {}
    for group in payload["latestGroupedPoints"]:
        if not isinstance(group, dict) or not isinstance(group.get("icon"), str):
            raise EcoCoachError("Points response contains an invalid group")
        icon = group["icon"]
        if icon in _POINT_CATEGORIES:
            if icon in recent:
                raise EcoCoachError("Points response contains a duplicate category")
            recent[icon] = _points(group.get("points"))
    return PointsSummary(_points(payload.get("points")), recent)


def parse_awards(payload: Any) -> tuple[PointsAward, ...]:
    """Keep only points from supported report events; discard all trip details."""
    if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
        raise EcoCoachError("Points report response is invalid")
    awards: list[PointsAward] = []
    seen: set[str] = set()
    for event in payload["events"]:
        if not isinstance(event, dict):
            raise EcoCoachError("Points report contains an invalid event")
        event_type = event.get("type")
        if not isinstance(event_type, str):
            raise EcoCoachError("Points report contains an invalid event type")
        category = _AWARD_CATEGORIES.get(event_type)
        if category is None:
            continue
        event_id, created = event.get("id"), event.get("createdAt")
        if not isinstance(event_id, str) or not event_id or event_id in seen or not isinstance(created, str):
            raise EcoCoachError("Points report contains an invalid award identity")
        try:
            timestamp = datetime.fromisoformat(created.replace("Z", "+00:00"))
        except ValueError as err:
            raise EcoCoachError("Points report contains an invalid award timestamp") from err
        if timestamp.tzinfo is None:
            raise EcoCoachError("Points report contains an award without a timezone")
        awards.append(PointsAward(event_id, category, _points(event.get("points")), timestamp))
        seen.add(event_id)
    return tuple(awards)


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
    summary = payload.get("pointsSummary")
    points = None
    if summary is not None:
        if not isinstance(summary, dict) or not isinstance(summary.get("sum"), dict):
            raise EcoCoachError("Personal statistics contains an invalid points summary")
        points = _number(summary["sum"].get("points"), "personal.points")
    if not values and points is None:
        raise EcoCoachError("Personal statistics response contains no supported metrics")
    return PersonalStatistics(
        values.get("drive_score"), values.get("avg_consumption"), values.get("saved_emissions"), points
    )


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

    def set_token(self, token: str) -> None:
        """Apply a rotated access token before the next request."""
        self._token = token

    async def async_personal_statistics(self, vin: str) -> PersonalStatistics:
        """Fetch personal statistics for one vehicle."""
        url = f"{BASE_URL}/api/v5/{vin}/statistics/personal"
        payload = await self._async_get(
            url, "personal", statistics_period(datetime.now(self._timezone).date(), self._timezone)
        )
        return parse_statistics(payload)

    async def async_period_statistics(self, vin: str) -> tuple[PeriodStatistics, PeriodStatistics, PeriodStatistics]:
        """Fetch daily, weekly, and monthly summaries from the captured route."""
        payload = await self._async_get(f"{BASE_URL}/api/v5/{vin}/statistics/all", endpoint="all")
        return parse_period_statistics(payload)

    async def async_points(self) -> PointsSummary:
        """Get the account-wide balance and last seven days of point categories."""
        start = (datetime.now(UTC) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        payload = await self._async_get(f"{BASE_URL}/api/v5/user/points", "points", {"from": start})
        return parse_points(payload)

    async def async_awards(self, vin: str, *, all_history: bool = False) -> tuple[PointsAward, ...]:
        """Read vehicle awards without retaining the full private report."""
        start = (
            "2000-01-01T00:00:00Z"
            if all_history
            else (datetime.now(UTC) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        payload = await self._async_get(
            f"{BASE_URL}/api/v5/{vin}/report",
            "report",
            {"from": start},
            timeout=90 if all_history else 15,
        )
        return parse_awards(payload)

    async def _async_get(
        self, url: str, endpoint: str, params: dict[str, str] | None = None, *, timeout: int = 15
    ) -> Any:
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
                timeout=timeout,
            ) as response:
                _LOGGER.debug("Eco Coach statistics %s response HTTP %d", endpoint, response.status)
                if response.status in (401, 403):
                    _LOGGER.warning("Eco Coach statistics %s authorization failed (HTTP %d)", endpoint, response.status)
                    raise EcoCoachAuthError("Eco Coach rejected the token")
                if response.status == 429:
                    _LOGGER.warning("Eco Coach statistics %s request rate limited (HTTP 429)", endpoint)
                    raise EcoCoachRateLimitError("Eco Coach rate limit reached")
                if response.status != 200:
                    _LOGGER.warning("Eco Coach statistics %s request failed (HTTP %d)", endpoint, response.status)
                    raise EcoCoachError(f"Statistics request failed (HTTP {response.status})")
                try:
                    payload = await response.json()
                except (ValueError, ClientError) as err:
                    raise EcoCoachError("Statistics response is not valid JSON") from err
        except (TimeoutError, ClientError) as err:
            raise EcoCoachConnectionError("Could not reach the Eco Coach statistics host") from err
        return payload
