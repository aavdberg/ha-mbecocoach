"""Synthetic tests for privacy-minimal report levels and challenge counts."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.mbecocoach.api import (
    EcoCoachAuthError,
    EcoCoachClient,
    EcoCoachData,
    EcoCoachError,
    EcoCoachRateLimitError,
    PeriodStatistics,
    PersonalStatistics,
    ReportData,
    ReportSummary,
    parse_report_summary,
)
from custom_components.mbecocoach.const import CONF_TOKEN, CONF_VIN
from custom_components.mbecocoach.coordinator import EcoCoachCoordinator
from custom_components.mbecocoach.sensor import (
    REPORT_SENSORS,
    EcoCoachSensor,
    async_setup_entry,
)


def test_report_summary_discards_non_scalar_fields() -> None:
    """Challenge contents are opaque; only array lengths survive parsing."""
    payload = {
        "userLevel": {
            "points": 1234,
            "currentLevel": 3,
            "progress": 0.375,
            "progressDescription": "synthetic-private-marker",
            "levels": ["synthetic-private-marker"],
        },
        "activeCommunityChallenges": [{"unverified": "synthetic-private-marker"}],
        "competitiveChallenges": ["synthetic-private-marker", None],
        "coachMessages": ["synthetic-private-marker"],
    }
    summary = parse_report_summary(payload)
    assert summary == ReportSummary(1234.0, 3.0, 0.375, 1, 2)
    assert "synthetic-private-marker" not in repr(summary)
    assert all(value is None or isinstance(value, (int, float)) for value in asdict(summary).values())
    payload["activeCommunityChallenges"].clear()
    assert summary.community_challenges == 1


@pytest.mark.parametrize("payload", [{}, {"userLevel": None}, {"userLevel": {}}])
def test_absent_summary_is_unknown(payload: dict) -> None:
    assert parse_report_summary(payload) == ReportSummary(None, None, None, None, None)


@pytest.mark.parametrize(
    "value", [True, "synthetic-private-marker", {}, [], float("nan"), float("inf"), -float("inf"), 10**400]
)
def test_invalid_optional_numbers_are_unknown(value: object, caplog: pytest.LogCaptureFixture) -> None:
    summary = parse_report_summary(
        {"userLevel": {"points": value, "currentLevel": value, "progress": value}, "competitiveChallenges": []}
    )
    assert summary == ReportSummary(None, None, None, None, 0)
    assert "Ignoring invalid optional report level field" in caplog.text
    assert "synthetic-private-marker" not in caplog.text


@pytest.mark.parametrize("value", [True, 7, "synthetic-private-marker", []])
def test_invalid_level_object_is_unknown(value: object, caplog: pytest.LogCaptureFixture) -> None:
    assert parse_report_summary({"userLevel": value}) == ReportSummary(None, None, None, None, None)
    assert "Ignoring invalid optional report field userLevel" in caplog.text
    assert "synthetic-private-marker" not in caplog.text


@pytest.mark.parametrize("value", [True, 0, "synthetic-private-marker", {}])
def test_invalid_challenge_arrays_are_unknown(value: object, caplog: pytest.LogCaptureFixture) -> None:
    assert parse_report_summary({"activeCommunityChallenges": value, "competitiveChallenges": value}) == ReportSummary(
        None, None, None, None, None
    )
    assert "Ignoring invalid optional report field" in caplog.text
    assert "synthetic-private-marker" not in caplog.text


def test_zero_and_provider_progress_scale_are_preserved() -> None:
    assert parse_report_summary(
        {
            "userLevel": {"points": 0, "currentLevel": 0, "progress": 37.5},
            "activeCommunityChallenges": [],
            "competitiveChallenges": [],
        }
    ) == ReportSummary(0.0, 0.0, 37.5, 0, 0)


def test_confirmed_pro_level_code_is_displayed_as_eco_pro() -> None:
    summary = parse_report_summary({"userLevel": {"currentLevel": "PRO"}})
    assert summary.current_level == "Eco Pro"


def test_unconfirmed_level_code_stays_unknown(caplog: pytest.LogCaptureFixture) -> None:
    summary = parse_report_summary({"userLevel": {"currentLevel": "UNVERIFIED_LEVEL_CODE"}})
    assert summary.current_level is None
    assert "UNVERIFIED_LEVEL_CODE" not in caplog.text


def test_malformed_optional_field_does_not_hide_other_values() -> None:
    assert parse_report_summary(
        {
            "userLevel": {"points": 100, "currentLevel": {}, "progress": 0.25},
            "activeCommunityChallenges": {},
            "competitiveChallenges": [],
        }
    ) == ReportSummary(100.0, None, 0.25, None, 0)


@pytest.mark.parametrize("payload", [None, [], "synthetic-private-marker"])
def test_invalid_report_object_fails(payload: object) -> None:
    with pytest.raises(EcoCoachError, match="Points report response is invalid"):
        parse_report_summary(payload)


@pytest.mark.asyncio
async def test_report_poll_uses_one_existing_request() -> None:
    response = MagicMock(status=200)
    response.json = AsyncMock(
        return_value={
            "events": [],
            "userLevel": {"points": 100, "currentLevel": 2, "progress": 0.5},
            "activeCommunityChallenges": [],
            "competitiveChallenges": [{}],
        }
    )
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=response)
    context.__aexit__ = AsyncMock(return_value=False)
    session = MagicMock()
    session.get.return_value = context
    client = EcoCoachClient(session, "synthetic-token")
    report = await client.async_report("synthetic-vehicle")
    assert report == ReportData((), ReportSummary(100.0, 2.0, 0.5, 0, 1))
    session.get.assert_called_once()
    assert session.get.call_args.args[0].endswith("/api/v5/synthetic-vehicle/report")
    assert set(session.get.call_args.kwargs["params"]) == {"from"}
    assert session.get.call_args.kwargs["timeout"] == 15
    assert session.get.call_args.kwargs["params"]["from"] != "2000-01-01T00:00:00Z"


@pytest.mark.asyncio
async def test_coordinator_only_merges_awards_into_history() -> None:
    client = MagicMock()
    client.async_personal_statistics = AsyncMock(return_value=PersonalStatistics(None, None, None))
    client.async_period_statistics = AsyncMock(return_value=(PeriodStatistics(None, None, None),) * 3)
    client.async_points = AsyncMock(return_value=None)
    client.async_report = AsyncMock(return_value=ReportData((), ReportSummary(100, 2, 0.5, 1, 0)))
    entry = MagicMock(data={CONF_VIN: "synthetic-vehicle", CONF_TOKEN: "synthetic-token"})
    coordinator = EcoCoachCoordinator(MagicMock(), client, "synthetic-vehicle", entry)
    coordinator.history = MagicMock()
    coordinator.history.async_merge = AsyncMock()
    result = await coordinator._async_update_data()
    assert result.report == client.async_report.return_value.summary
    coordinator.history.async_merge.assert_awaited_once_with(())
    client.async_report.return_value = ReportData((), ReportSummary(None, None, None, None, None))
    result = await coordinator._async_update_data()
    assert result.report.level_points is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected"),
    [(EcoCoachAuthError(), ConfigEntryAuthFailed), (EcoCoachRateLimitError(), UpdateFailed)],
)
async def test_report_errors_preserve_coordinator_failure_behavior(error: Exception, expected: type[Exception]) -> None:
    client = MagicMock()
    client.async_personal_statistics = AsyncMock()
    client.async_period_statistics = AsyncMock(return_value=(1, 2, 3))
    client.async_points = AsyncMock()
    client.async_report = AsyncMock(side_effect=error)
    entry = MagicMock(data={CONF_VIN: "synthetic-vehicle", CONF_TOKEN: "synthetic-token"})
    coordinator = EcoCoachCoordinator(MagicMock(), client, "synthetic-vehicle", entry)
    with pytest.raises(expected):
        await coordinator._async_update_data()


@pytest.mark.parametrize("description", REPORT_SENSORS, ids=lambda description: description.key)
@pytest.mark.parametrize(
    "summary",
    [
        ReportSummary(100.0, 2.0, 0.125, 1, 0),
        ReportSummary(1234.0, "Eco Pro", 0.28, 5, 0),
        ReportSummary(0, 0, 0, 0, 0),
    ],
)
def test_report_sensors_have_no_private_attributes(
    description: SensorEntityDescription, summary: ReportSummary
) -> None:
    coordinator = MagicMock()
    coordinator.data = EcoCoachData(
        PersonalStatistics(None, None, None),
        *(PeriodStatistics(None, None, None),) * 3,
        report=summary,
    )
    entity = EcoCoachSensor(coordinator, MagicMock(data={CONF_VIN: "synthetic-vehicle"}), description)
    entity.platform_data = SimpleNamespace(
        platform_name="mbecocoach",
        domain="sensor",
        default_language_platform_translations={},
    )
    assert entity.native_value == getattr(summary, description.key.removeprefix("report_"))
    assert entity.state == entity.native_value
    assert entity.unique_id == f"synthetic-vehicle_{description.key}"
    other = EcoCoachSensor(coordinator, MagicMock(data={CONF_VIN: "other-synthetic-vehicle"}), description)
    assert other.unique_id != entity.unique_id
    assert entity.extra_state_attributes is None
    assert entity.native_unit_of_measurement is None
    coordinator.data = EcoCoachData(
        PersonalStatistics(None, None, None),
        *(PeriodStatistics(None, None, None),) * 3,
    )
    assert entity.native_value is None


@pytest.mark.asyncio
async def test_report_sensor_registration_and_translations() -> None:
    entry = MagicMock(data={CONF_VIN: "synthetic-vehicle"})
    add = MagicMock()
    await async_setup_entry(MagicMock(), entry, add)
    registered = {entity.entity_description.key for entity in add.call_args.args[0]}
    keys = {description.key for description in REPORT_SENSORS}
    assert keys <= registered
    root = Path(__file__).parents[1] / "custom_components" / "mbecocoach"
    for path in (root / "strings.json", *(root / "translations").glob("*.json")):
        translations = json.loads(path.read_text(encoding="utf-8"))["entity"]["sensor"]
        assert keys <= translations.keys()
