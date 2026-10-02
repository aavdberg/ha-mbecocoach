"""Tests for captured Eco Coach API behavior."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest

from custom_components.mbecocoach.api import (
    EcoCoachAuthError,
    EcoCoachClient,
    EcoCoachConnectionError,
    EcoCoachError,
    EcoCoachRateLimitError,
    PeriodStatistics,
    PersonalStatistics,
    parse_period_statistics,
    parse_statistics,
    statistics_period,
)

VIN = "WDD12345678901234"


def card(icon: str, unit: str, value: object) -> dict:
    """Construct a synthetic card with the captured response layout."""
    return {"icon": icon, "entryTop": {"label": "example", "value": {"value": value, "unit": unit}}}


def test_parse_statistics() -> None:
    """Extract the observed icons and units, including the second consumption card."""
    assert parse_statistics(
        {
            "topCards": [
                card("CONSUMPTION_ELECTRIC", "KWH", 25),
                card("CO2", "KG", 5.1285),
                card("CONSUMPTION_ELECTRIC", "KWH100KM", 19.503),
                card("DRIVING", "PERCENT", 91.047),
            ],
            "bottomCards": [],
            "pointsSummary": {"sum": {"points": 2675}},
        }
    ) == PersonalStatistics(91.047, 19.503, 5.1285, 2675.0)
    assert parse_statistics({"topCards": [card("DRIVING", "PERCENT", 76)]}) == PersonalStatistics(76.0, None, None)


def test_personal_points_are_not_lifetime_points() -> None:
    """Read only the aggregate from the captured personal statistics response."""
    payload = {"topCards": [card("DRIVING", "PERCENT", 91)], "pointsSummary": {"sum": {"points": 1200}}}
    assert parse_statistics(payload).points == 1200.0
    assert parse_statistics({"topCards": [], "pointsSummary": {"sum": {"points": 0}}}) == PersonalStatistics(
        None, None, None, 0.0
    )


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {},
        {"points": 5},
        {"topCards": "not-a-list"},
        {"topCards": [card("DRIVING", "PERCENT", "91")]},
        {"topCards": [card("DRIVING", "PERCENT", True)]},
        {"topCards": [card("DRIVING", "PERCENT", float("nan"))]},
        {"topCards": [card("DRIVING", "PERCENT", 50), card("DRIVING", "PERCENT", 51)]},
        {"topCards": [card("DRIVING", "KM", 50)]},
        {"topCards": [card("DRIVING", "PERCENT", 50)], "pointsSummary": []},
        {"topCards": [card("DRIVING", "PERCENT", 50)], "pointsSummary": {"sum": {"points": True}}},
    ],
)
def test_parse_statistics_rejects_unsupported_payload(payload: object) -> None:
    """Invalid responses must not silently publish fabricated sensors."""
    with pytest.raises(EcoCoachError):
        parse_statistics(payload)


def test_statistics_period() -> None:
    """Match captured local Monday-Sunday windows converted to UTC."""
    assert statistics_period(date(2026, 10, 1), ZoneInfo("Europe/Amsterdam")) == {
        "from": "2026-09-27T22:00:00Z",
        "to": "2026-10-04T21:59:59Z",
        "compareFrom": "2026-09-20T22:00:00Z",
        "compareTo": "2026-09-27T21:59:59Z",
    }


def test_statistics_period_dst_change() -> None:
    """Local week boundaries keep the correct UTC offset across a DST switch."""
    params = statistics_period(date(2026, 10, 28), ZoneInfo("Europe/Amsterdam"))
    assert params["from"] == "2026-10-25T23:00:00Z"
    assert params["compareFrom"] == "2026-10-18T22:00:00Z"


def test_parse_period_statistics() -> None:
    """Read only period aggregates, never trip or chart payloads."""
    period = {
        "driveScoreStatistics": {"driveScore": 76},
        "consumptionStatistics": {"electricConsumption": {"value": 22.0, "unit": "KWH100KM"}},
        "pointsSummary": {"sum": {"points": 2675}},
        "consumptionChartDataset": [{"x": 1, "y": 2}],
    }
    payload = {"dailyStatistics": period, "weeklyStatistics": period, "monthlyStatistics": period}
    result = parse_period_statistics(payload)
    assert result == (PeriodStatistics(76, 22.0, 2675),) * 3


def test_parse_period_optional_fields() -> None:
    """Other fuel types and absent optional fields never become fabricated readings."""
    period = {"consumptionStatistics": {"electricConsumption": {"value": 5, "unit": "L100KM"}}}
    result = parse_period_statistics({"dailyStatistics": period, "weeklyStatistics": {}, "monthlyStatistics": {}})
    assert result == (PeriodStatistics(None, None, None),) * 3


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {"dailyStatistics": {}},
        {"dailyStatistics": [], "weeklyStatistics": {}, "monthlyStatistics": {}},
        {
            "dailyStatistics": {"driveScoreStatistics": {"driveScore": "bad"}},
            "weeklyStatistics": {},
            "monthlyStatistics": {},
        },
        {
            "dailyStatistics": {"pointsSummary": {"sum": {"points": True}}},
            "weeklyStatistics": {},
            "monthlyStatistics": {},
        },
    ],
)
def test_parse_period_rejects_bad_data(payload: object) -> None:
    """Reject malformed documented period fields without success-shaped defaults."""
    with pytest.raises(EcoCoachError):
        parse_period_statistics(payload)


def make_client(status: int, payload: object = None) -> tuple[EcoCoachClient, MagicMock]:
    """Build an HTTP context manager with no network requests."""
    response = MagicMock(status=status)
    response.json = AsyncMock(return_value=payload)
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=response)
    context.__aexit__ = AsyncMock(return_value=False)
    session = MagicMock()
    session.get.return_value = context
    return EcoCoachClient(session, "sample-token"), session


@pytest.mark.asyncio
async def test_personal_statistics_request() -> None:
    """Use the captured path, parameters, and app headers without exposing credentials."""
    client, session = make_client(200, {"topCards": [card("DRIVING", "PERCENT", 91)]})
    assert await client.async_personal_statistics(VIN) == PersonalStatistics(91.0, None, None)
    args, kwargs = session.get.call_args
    assert args[0].endswith(f"/api/v5/{VIN}/statistics/personal")
    assert kwargs["headers"] == {
        "Authorization": "Bearer sample-token",
        "ecocoach-app-version": "5.7.0",
        "ecocoach-platform": "iOS",
    }
    assert set(kwargs["params"]) == {"from", "to", "compareFrom", "compareTo"}


@pytest.mark.asyncio
async def test_period_request_has_no_query_parameters() -> None:
    """The captured statistics/all call has no query string."""
    periods = {name: {} for name in ("dailyStatistics", "weeklyStatistics", "monthlyStatistics")}
    client, session = make_client(200, periods)
    assert await client.async_period_statistics(VIN) == (PeriodStatistics(None, None, None),) * 3
    args, kwargs = session.get.call_args
    assert args[0].endswith(f"/api/v5/{VIN}/statistics/all")
    assert kwargs["params"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "error"),
    [(401, EcoCoachAuthError), (403, EcoCoachAuthError), (429, EcoCoachRateLimitError), (500, EcoCoachError)],
)
async def test_http_errors(status: int, error: type[Exception]) -> None:
    """Authentication, throttling, and server errors remain distinguishable."""
    client, _ = make_client(status)
    with pytest.raises(error):
        await client.async_personal_statistics(VIN)


@pytest.mark.asyncio
async def test_connection_failure() -> None:
    """Surface timeouts without leaking URLs or bearer tokens."""
    client, session = make_client(200)
    session.get.side_effect = TimeoutError
    with pytest.raises(EcoCoachConnectionError, match="Could not reach"):
        await client.async_personal_statistics(VIN)


@pytest.mark.asyncio
async def test_non_json_response() -> None:
    """Reject malformed JSON response."""
    client, session = make_client(200)
    context = session.get.return_value
    response = await context.__aenter__()
    response.json.side_effect = ValueError("invalid")
    with pytest.raises(EcoCoachError, match="not valid JSON"):
        await client.async_personal_statistics(VIN)
