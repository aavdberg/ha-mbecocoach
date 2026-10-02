"""Schema and privacy tests for account points and individual awards."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.mbecocoach import async_unload_entry
from custom_components.mbecocoach.api import (
    EcoCoachClient,
    EcoCoachData,
    EcoCoachError,
    PeriodStatistics,
    PersonalStatistics,
    PointsAward,
    PointsSummary,
    parse_awards,
    parse_points,
)
from custom_components.mbecocoach.button import EcoCoachHistoryButton
from custom_components.mbecocoach.const import CONF_VIN, DOMAIN
from custom_components.mbecocoach.event import EcoCoachPointsEvent
from custom_components.mbecocoach.points_history import PointsHistory
from custom_components.mbecocoach.sensor import POINT_SENSORS, EcoCoachSensor

VIN = "WDD12345678901234"


def test_points_summary_parses_only_known_categories() -> None:
    """A balance and grouped awards must not be confused with period points."""
    summary = parse_points(
        {
            "points": 100000,
            "latestGroupedPoints": [
                {"icon": "DRIVING", "points": 50, "private": "ignored"},
                {"icon": "PERSONAL_CHALLENGE", "points": 0},
                {"icon": "UNRECOGNIZED", "points": 99},
            ],
        }
    )
    assert summary == PointsSummary(100000, {"DRIVING": 50, "PERSONAL_CHALLENGE": 0})


@pytest.mark.parametrize(
    "payload",
    [
        {"points": True, "latestGroupedPoints": []},
        {"points": -1, "latestGroupedPoints": []},
        {"points": 1, "latestGroupedPoints": [{"icon": "DRIVING", "points": 1.5}]},
        {"points": 1, "latestGroupedPoints": [{"icon": "DRIVING", "points": 2}, {"icon": "DRIVING", "points": 3}]},
        {"points": 1},
    ],
)
def test_points_summary_rejects_invalid_data(payload: dict) -> None:
    with pytest.raises(EcoCoachError):
        parse_points(payload)


def test_report_retains_only_minimal_award_metadata() -> None:
    """Do not persist locations, trips, messages, or account names."""
    awards = parse_awards(
        {
            "events": [
                {
                    "id": "synthetic-id",
                    "type": "DRIVE",
                    "points": 50,
                    "createdAt": "2026-01-02T03:04:05Z",
                    "tripLocation": "private location",
                    "coachingHintMessage": "private message",
                },
                {"id": "other-id", "type": "UNRECOGNIZED", "points": 10, "createdAt": "2026-01-02T03:05:00Z"},
            ],
            "coachMessages": [{"message": "private message"}],
        }
    )
    assert awards == (PointsAward("synthetic-id", "driving", 50, datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)),)
    assert "private location" not in repr(awards)
    assert "private message" not in repr(awards)


@pytest.mark.parametrize(
    "event",
    [
        {"id": "id", "type": "DRIVE", "points": True, "createdAt": "2026-01-02T03:04:05Z"},
        {"id": "id", "type": "DRIVE", "points": 50, "createdAt": "bad"},
        {"id": "id", "type": "DRIVE", "points": 50, "createdAt": "2026-01-02T03:04:05"},
        {"id": "id", "type": ["DRIVE"], "points": 50, "createdAt": "2026-01-02T03:04:05Z"},
    ],
)
def test_report_rejects_invalid_awards(event: dict) -> None:
    with pytest.raises(EcoCoachError):
        parse_awards({"events": [event]})


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("account_total_points", 100000),
        ("recent_driving_points", 50),
        ("recent_charging_points", 0),
        ("recent_parking_points", 25),
        ("recent_personal_challenge_points", 0),
    ],
)
def test_points_sensors(key: str, expected: int) -> None:
    coordinator = MagicMock()
    coordinator.data = EcoCoachData(
        PersonalStatistics(None, None, None),
        *(PeriodStatistics(None, None, None) for _ in range(3)),
        points=PointsSummary(100000, {"DRIVING": 50, "PARKING": 25}),
    )
    description = next(desc for desc in POINT_SENSORS if desc.key == key)
    entity = EcoCoachSensor(coordinator, MagicMock(data={CONF_VIN: VIN}), description)
    assert entity.native_value == expected
    assert entity.suggested_display_precision == 0


def test_award_event_only_emits_new_ids() -> None:
    """Existing reports are a baseline; later awards enter HA history once."""
    old = PointsAward("existing", "driving", 50, datetime(2026, 1, 2, 3, 4, tzinfo=UTC))
    new = PointsAward("new", "parking", 25, datetime(2026, 1, 2, 4, 5, tzinfo=UTC))
    coordinator = MagicMock()
    coordinator.data = MagicMock(awards=(old,))
    entity = EcoCoachPointsEvent(coordinator, MagicMock(data={CONF_VIN: VIN}))
    entity.entity_id = "event.eco_coach_points_awarded"
    entity.async_write_ha_state = MagicMock()
    assert entity.state is None
    coordinator.data.awards = (new, old)
    entity._handle_coordinator_update()
    assert entity.state_attributes == {
        "event_type": "parking",
        "points": 25,
        "occurred_at": new.occurred_at.isoformat(),
    }
    entity.async_write_ha_state.assert_called_once()
    entity._handle_coordinator_update()
    assert entity.async_write_ha_state.call_count == 2


@pytest.mark.asyncio
async def test_history_is_replaced_and_paginated_without_extra_fields() -> None:
    """The reimport button replaces only the integration-owned minimal archive."""
    award = PointsAward("private-synthetic-id", "charging", 50, datetime(2026, 1, 2, tzinfo=UTC))
    with patch("custom_components.mbecocoach.points_history.Store") as storage:
        storage.return_value.async_load = AsyncMock(return_value=None)
        storage.return_value.async_save = AsyncMock()
        history = PointsHistory(MagicMock(), "synthetic-entry")
        assert not await history.async_load()
        await history.async_replace((award,))
        saved = storage.return_value.async_save.await_args.args[0]
        assert set(saved) == {"awards"}
        assert saved["awards"] == [
            {
                "id": "private-synthetic-id",
                "category": "charging",
                "points": 50,
                "occurred_at": "2026-01-02T00:00:00+00:00",
            }
        ]
        assert history.page(0, 1) == {
            "total": 1,
            "offset": 0,
            "awards": [{"category": "charging", "points": 50, "occurred_at": "2026-01-02T00:00:00+00:00"}],
        }
        assert history.latest("charging") == award
        await history.async_merge((award,))
        storage.return_value.async_save.assert_awaited_once()
        await history.async_replace(())
        assert history.count == 0


@pytest.mark.asyncio
async def test_history_loads_after_restart_without_fetching_again() -> None:
    """A preexisting cache avoids another full report request on startup."""
    saved = {
        "awards": [{"id": "synthetic", "category": "driving", "points": 75, "occurred_at": "2026-01-02T00:00:00+00:00"}]
    }
    with patch("custom_components.mbecocoach.points_history.Store") as storage:
        storage.return_value.async_load = AsyncMock(return_value=saved)
        history = PointsHistory(MagicMock(), "synthetic-entry")
        assert await history.async_load()
        assert history.count == 1
        assert history.page(1, 50)["awards"] == []


@pytest.mark.asyncio
async def test_manual_history_button_only_calls_reimport() -> None:
    coordinator = MagicMock()
    coordinator.async_replace_history = AsyncMock()
    button = EcoCoachHistoryButton(coordinator, MagicMock(data={CONF_VIN: VIN}))
    await button.async_press()
    coordinator.async_replace_history.assert_awaited_once()


@pytest.mark.asyncio
async def test_points_requests_use_observed_routes_and_bounded_recent_window() -> None:
    """The full report is a manual/first-install fetch, not a 15-minute poll."""
    response = MagicMock(status=200)
    response.json = AsyncMock(return_value={"points": 0, "latestGroupedPoints": []})
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=response)
    context.__aexit__ = AsyncMock(return_value=False)
    session = MagicMock()
    session.get.return_value = context
    client = EcoCoachClient(session, "sample-token")
    assert (await client.async_points()).total == 0
    assert session.get.call_args.args[0].endswith("/api/v5/user/points")
    assert set(session.get.call_args.kwargs["params"]) == {"from"}
    response.json.return_value = {"events": []}
    await client.async_awards(VIN)
    assert session.get.call_args.args[0].endswith(f"/api/v5/{VIN}/report")
    assert session.get.call_args.kwargs["params"]["from"] != "2000-01-01T00:00:00Z"
    await client.async_awards(VIN, all_history=True)
    assert session.get.call_args.kwargs["params"] == {"from": "2000-01-01T00:00:00Z"}


def test_latest_award_sensor_has_only_time_attribute() -> None:
    """Expose an imported older award without persisting trip/report metadata."""
    award = PointsAward("synthetic", "driving", 75, datetime(2026, 1, 2, tzinfo=UTC))
    coordinator = MagicMock()
    coordinator.data = MagicMock(awards=())
    coordinator.history = MagicMock()
    coordinator.history.latest.return_value = award
    description = next(desc for desc in POINT_SENSORS if desc.key == "latest_driving_award")
    entity = EcoCoachSensor(coordinator, MagicMock(data={CONF_VIN: VIN}), description)
    assert entity.native_value == 75
    assert entity.extra_state_attributes == {"occurred_at": "2026-01-02T00:00:00+00:00"}
    coordinator.history.latest.assert_called_with("driving")


@pytest.mark.asyncio
async def test_unload_removes_history_service_only_after_last_loaded_entry() -> None:
    """Disabled/unloaded configured entries must not keep the response service."""
    hass = MagicMock()
    hass.data = {DOMAIN: {"first", "second"}}
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    with patch("custom_components.mbecocoach.remove_extra_js_url") as remove_js:
        await async_unload_entry(hass, MagicMock(entry_id="first"))
        assert hass.data[DOMAIN] == {"second"}
        hass.services.async_remove.assert_not_called()
        remove_js.assert_not_called()
        await async_unload_entry(hass, MagicMock(entry_id="second"))
        remove_js.assert_called_once()
    hass.services.async_remove.assert_called_once_with(DOMAIN, "get_points_history")
    assert DOMAIN not in hass.data
