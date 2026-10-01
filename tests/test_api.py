"""Tests for captured Eco Coach API behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.mbecocoach.api import (
    EcoCoachAuthError,
    EcoCoachClient,
    EcoCoachConnectionError,
    EcoCoachError,
    EcoCoachRateLimitError,
    PersonalStatistics,
    parse_statistics,
)

VIN = "WDD12345678901234"


def test_parse_statistics() -> None:
    """Map only supported numeric metrics."""
    assert parse_statistics(
        {"driveScore": 91.047, "avgConsumption": 19.503, "savedEmissions": 5.1285, "unknown": 12}
    ) == PersonalStatistics(91.047, 19.503, 5.1285)
    assert parse_statistics({"driveScore": 76}) == PersonalStatistics(76.0, None, None)


@pytest.mark.parametrize(
    "payload",
    [None, [], {}, {"points": 5}, {"driveScore": "91"}, {"driveScore": True}, {"driveScore": float("nan")}],
)
def test_parse_statistics_rejects_unsupported_payload(payload: object) -> None:
    """Invalid responses must not silently publish fabricated sensors."""
    with pytest.raises(EcoCoachError):
        parse_statistics(payload)


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
    """Use the captured path and bearer header without exposing credentials."""
    client, session = make_client(200, {"driveScore": 91})
    assert await client.async_personal_statistics(VIN) == PersonalStatistics(91.0, None, None)
    args, kwargs = session.get.call_args
    assert args[0].endswith(f"/api/v5/{VIN}/statistics/personal")
    assert kwargs["headers"] == {"Authorization": "Bearer sample-token"}


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
