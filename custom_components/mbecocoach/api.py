"""Client for the observed Eco Coach personal statistics endpoint."""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
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
    """Summary metrics and whitelisted history; no route, message, or account details."""

    personal: PersonalStatistics
    daily: PeriodStatistics
    weekly: PeriodStatistics
    monthly: PeriodStatistics
    points: PointsSummary | None = None
    awards: tuple[PointsAward, ...] = ()
    report: ReportSummary | None = None


@dataclass(frozen=True)
class ReportSummary:
    """Optional level summaries and counts, never raw challenge details."""

    level_points: float | None
    current_level: float | str | None
    level_progress: float | None
    community_challenges: int | None
    competitive_challenges: int | None


@dataclass(frozen=True)
class ReportData:
    """Whitelisted summaries extracted from a single vehicle report request."""

    awards: tuple[PointsAward, ...]
    summary: ReportSummary


@dataclass(frozen=True)
class PointsSummary:
    """Account total and recent grouped points, without activity details."""

    total: int
    recent: dict[str, int]


@dataclass(frozen=True)
class DriveDetails:
    """A private, location-free summary of one confirmed driving report event."""

    drive_score: float | None
    distance_km: float | None
    electric_consumption: float | None
    co2_emissions_kg: float | None
    duration_seconds: int | None
    start_time: datetime | None
    temperature_c: float | None
    battery_percent_change: int | None


@dataclass(frozen=True)
class PointsAward:
    """Award metadata and optional location-free driving summary."""

    id: str
    category: str
    points: int
    occurred_at: datetime
    drive_details: DriveDetails | None = None


_POINT_CATEGORIES = frozenset({"DRIVING", "CHARGING", "PARKING", "PERSONAL_CHALLENGE"})
_AWARD_CATEGORIES = {"DRIVE": "driving", "CHARGE": "charging", "PARK": "parking"}


def _points(value: Any) -> int:
    """Only whole, nonnegative point balances are supported."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise EcoCoachError("Points response contains invalid points")
    return value


def _event_number(
    event: dict[str, Any], key: str, field: str, unit: str | None = None, *, nonnegative: bool = True
) -> float | None:
    """Read a confirmed optional numeric field from a report event."""
    value = event.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise EcoCoachError(f"Points report field {field} is invalid")
    if unit is not None and value.get("unit") != unit:
        raise EcoCoachError(f"Points report field {field} has an unsupported unit")
    number = _number(value.get("value"), field)
    if nonnegative and number is not None and number < 0:
        raise EcoCoachError(f"Points report field {field} is negative")
    return number


def _event_integer(event: dict[str, Any], key: str, field: str, minimum: int, maximum: int) -> int | None:
    """Read a bounded whole-number report field."""
    value = event.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise EcoCoachError(f"Points report field {field} is invalid")
    return value


def _event_timestamp(event: dict[str, Any], key: str, field: str) -> datetime | None:
    """Read an optional timezone-aware report timestamp."""
    value = event.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise EcoCoachError(f"Points report field {field} is invalid")
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as err:
        raise EcoCoachError(f"Points report field {field} is invalid") from err
    if timestamp.tzinfo is None:
        raise EcoCoachError(f"Points report field {field} has no timezone")
    return timestamp


def _optional_drive_value[T](field: str, read: Callable[[], T]) -> T | None:
    """Ignore malformed optional details without rejecting a valid driving award."""
    try:
        return read()
    except EcoCoachError, OverflowError:
        _LOGGER.warning("Ignoring invalid optional driving detail field %s", field)
        return None


def parse_drive_details(event: dict[str, Any]) -> DriveDetails | None:
    """Extract only confirmed trip summary values; discard route, hints and messages."""

    def score() -> float | None:
        value = _number(event.get("driveScore"), "driveScore")
        if value is not None and not 0 <= value <= 100:
            raise EcoCoachError("Points report field driveScore is out of range")
        return value

    drive_score = _optional_drive_value("driveScore", score)
    distance_km = _optional_drive_value(
        "distanceTraveled", lambda: _event_number(event, "distanceTraveled", "distanceTraveled", "KM")
    )
    electric_consumption = _optional_drive_value(
        "electricConsumption", lambda: _event_number(event, "electricConsumption", "electricConsumption", "KWH100KM")
    )
    co2_emissions_kg = _optional_drive_value(
        "co2Emissions", lambda: _event_number(event, "co2Emissions", "co2Emissions", "KG")
    )
    duration_seconds = _optional_drive_value(
        "durationInSec", lambda: _event_integer(event, "durationInSec", "durationInSec", 0, 86_400)
    )
    start_time = _optional_drive_value("startTime", lambda: _event_timestamp(event, "startTime", "startTime"))
    temperature = _optional_drive_value(
        "temperatureAvg", lambda: _event_number(event, "temperatureAvg", "temperatureAvg", "CELSIUS", nonnegative=False)
    )
    battery_change = _optional_drive_value("socDiff", lambda: _event_integer(event, "socDiff", "socDiff", -100, 100))
    details = DriveDetails(
        drive_score,
        distance_km,
        electric_consumption,
        co2_emissions_kg,
        duration_seconds,
        start_time,
        temperature,
        battery_change,
    )
    return (
        details
        if any(
            value is not None
            for value in (
                drive_score,
                distance_km,
                electric_consumption,
                co2_emissions_kg,
                duration_seconds,
                start_time,
                temperature,
                battery_change,
            )
        )
        else None
    )


def drive_details_to_storage(details: DriveDetails) -> dict[str, Any]:
    """Serialize the explicit trip-summary whitelist for private local storage."""
    return {
        "drive_score": details.drive_score,
        "distance_km": details.distance_km,
        "electric_consumption": details.electric_consumption,
        "co2_emissions_kg": details.co2_emissions_kg,
        "duration_seconds": details.duration_seconds,
        "start_time": details.start_time.isoformat() if details.start_time else None,
        "temperature_c": details.temperature_c,
        "battery_percent_change": details.battery_percent_change,
    }


def parse_stored_drive_details(payload: Any) -> DriveDetails:
    """Validate the local, flattened driving-summary record."""
    fields = {
        "drive_score",
        "distance_km",
        "electric_consumption",
        "co2_emissions_kg",
        "duration_seconds",
        "start_time",
        "temperature_c",
        "battery_percent_change",
    }
    if not isinstance(payload, dict) or set(payload) != fields:
        raise EcoCoachError("Saved points history contains invalid driving details")

    def number(key: str, *, maximum: float | None = None) -> float | None:
        value = _number(payload[key], key)
        if value is not None and (value < 0 or (maximum is not None and value > maximum)):
            raise EcoCoachError(f"Saved points history contains invalid {key}")
        return value

    duration = payload["duration_seconds"]
    if duration is not None and (
        isinstance(duration, bool) or not isinstance(duration, int) or not 0 <= duration <= 86_400
    ):
        raise EcoCoachError("Saved points history contains invalid duration_seconds")
    battery_change = payload["battery_percent_change"]
    if battery_change is not None and (
        isinstance(battery_change, bool) or not isinstance(battery_change, int) or not -100 <= battery_change <= 100
    ):
        raise EcoCoachError("Saved points history contains invalid battery_percent_change")

    start_time = payload["start_time"]
    if start_time is not None:
        if not isinstance(start_time, str):
            raise EcoCoachError("Saved points history contains invalid start_time")
        try:
            start_time = datetime.fromisoformat(start_time)
        except ValueError as err:
            raise EcoCoachError("Saved points history contains invalid start_time") from err
        if start_time.tzinfo is None:
            raise EcoCoachError("Saved points history contains a start_time without a timezone")

    return DriveDetails(
        number("drive_score", maximum=100),
        number("distance_km"),
        number("electric_consumption"),
        number("co2_emissions_kg"),
        duration,
        start_time,
        _number(payload["temperature_c"], "temperature_c"),
        battery_change,
    )


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
    """Keep supported awards and whitelisted drive summaries; discard other report details."""
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
        details = parse_drive_details(event) if category == "driving" else None
        awards.append(PointsAward(event_id, category, _points(event.get("points")), timestamp, details))
        seen.add(event_id)
    return tuple(awards)


def _number(value: Any, field: str) -> float | None:
    """Validate API numbers, excluding booleans and non-finite values."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise EcoCoachError(f"Statistics field {field} is not numeric")
    return float(value)


def parse_report_summary(payload: Any) -> ReportSummary:
    """Read only captured scalar fields and list lengths without inferring units."""
    if not isinstance(payload, dict):
        raise EcoCoachError("Points report response is invalid")
    level = payload.get("userLevel")
    if level is not None and not isinstance(level, dict):
        _LOGGER.warning("Ignoring invalid optional report field userLevel")
        level = None

    def number(key: str) -> float | str | None:
        if level is None:
            return None
        value = level.get(key)
        if key == "currentLevel" and value == "PRO":
            return "Eco Pro"
        try:
            return _number(value, key)
        except EcoCoachError, OverflowError:
            _LOGGER.warning("Ignoring invalid optional report level field %s", key)
            return None

    def count(key: str) -> int | None:
        value = payload.get(key)
        if value is None:
            return None
        if not isinstance(value, list):
            _LOGGER.warning("Ignoring invalid optional report field %s", key)
            return None
        return len(value)

    return ReportSummary(
        number("points"),
        number("currentLevel"),
        number("progress"),
        count("activeCommunityChallenges"),
        count("competitiveChallenges"),
    )


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
        return (await self.async_report(vin, all_history=all_history)).awards

    async def async_report(self, vin: str, *, all_history: bool = False) -> ReportData:
        """Read awards and optional summaries in the existing single report call."""
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
        return ReportData(parse_awards(payload), parse_report_summary(payload))

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
