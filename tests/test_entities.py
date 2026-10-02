"""Tests for per-vehicle Eco Coach sensor summaries."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.mbecocoach.api import EcoCoachData, PeriodStatistics, PersonalStatistics
from custom_components.mbecocoach.const import CONF_VIN
from custom_components.mbecocoach.sensor import PERIOD_SENSORS, SENSORS, EcoCoachSensor

VIN = "WDD12345678901234"


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("personal_drive_score", 91.0),
        ("personal_avg_consumption", 19.5),
        ("personal_saved_emissions", 5.1),
        ("personal_points", 1200.0),
        ("daily_drive_score", 76.0),
        ("daily_consumption", 22.0),
        ("daily_points", 2675.0),
        ("weekly_drive_score", 79.0),
        ("weekly_consumption", 21.5),
        ("weekly_points", 15375.0),
        ("monthly_drive_score", 87.0),
        ("monthly_consumption", 19.9),
        ("monthly_points", 82850.0),
    ],
)
def test_sensor_value_and_identity(key: str, expected: float) -> None:
    """Expose correct period values while keeping original personal entity IDs."""
    coordinator = MagicMock()
    coordinator.data = EcoCoachData(
        PersonalStatistics(91.0, 19.5, 5.1, 1200.0),
        PeriodStatistics(76.0, 22.0, 2675.0),
        PeriodStatistics(79.0, 21.5, 15375.0),
        PeriodStatistics(87.0, 19.9, 82850.0),
    )
    entry = MagicMock(data={CONF_VIN: VIN})
    description = next(desc for desc in (*SENSORS, *PERIOD_SENSORS) if desc.key == key)
    entity = EcoCoachSensor(coordinator, entry, description)
    assert entity.native_value == expected
    assert entity.unique_id == f"{VIN}_{key.removeprefix('personal_')}"
    assert entity.device_info["identifiers"] == {("mbecocoach", VIN)}


def test_missing_sensor_value() -> None:
    """Absent metrics stay unknown and do not become zero."""
    coordinator = MagicMock()
    coordinator.data = EcoCoachData(
        PersonalStatistics(None, None, None),
        PeriodStatistics(None, None, None),
        PeriodStatistics(None, None, None),
        PeriodStatistics(None, None, None),
    )
    entity = EcoCoachSensor(coordinator, MagicMock(data={CONF_VIN: VIN}), PERIOD_SENSORS[0])
    assert entity.native_value is None


@pytest.mark.parametrize(
    ("key", "precision"),
    [
        ("personal_drive_score", 1),
        ("personal_avg_consumption", 1),
        ("personal_saved_emissions", 2),
        ("personal_points", 0),
        *(
            (f"{period}_{metric}", 0 if metric == "points" else 1)
            for period in ("daily", "weekly", "monthly")
            for metric in ("drive_score", "consumption", "points")
        ),
    ],
)
def test_sensor_display_precision_keeps_native_value(key: str, precision: int) -> None:
    """Suggest concise display without rounding sensor states used by automations."""
    coordinator = MagicMock()
    coordinator.data = EcoCoachData(
        PersonalStatistics(83.1751165623556, 20.9048872180451, 34.979, 2075.0),
        PeriodStatistics(83.1751165623556, 20.9048872180451, 2075.0),
        PeriodStatistics(83.1751165623556, 20.9048872180451, 2075.0),
        PeriodStatistics(83.1751165623556, 20.9048872180451, 2075.0),
    )
    description = next(desc for desc in (*SENSORS, *PERIOD_SENSORS) if desc.key == key)
    entity = EcoCoachSensor(coordinator, MagicMock(data={CONF_VIN: VIN}), description)
    assert description.suggested_display_precision == precision
    assert entity.suggested_display_precision == precision
    metric = key.split("_", 1)[1]
    assert entity.native_value == getattr(getattr(coordinator.data, key.split("_", 1)[0]), metric)
