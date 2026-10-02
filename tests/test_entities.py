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
