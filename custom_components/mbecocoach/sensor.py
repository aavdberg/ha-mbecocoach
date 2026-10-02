"""Observed Eco Coach personal statistics as Home Assistant sensors."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EcoCoachConfigEntry
from .api import PointsAward
from .const import CONF_VIN, DOMAIN
from .coordinator import EcoCoachCoordinator

SENSORS = (
    SensorEntityDescription(
        key="personal_drive_score",
        translation_key="drive_score",
        icon="mdi:car-speed-limiter",
        native_unit_of_measurement="%",
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="personal_avg_consumption",
        translation_key="avg_consumption",
        icon="mdi:lightning-bolt",
        native_unit_of_measurement="kWh/100 km",
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="personal_saved_emissions",
        translation_key="saved_emissions",
        icon="mdi:leaf",
        native_unit_of_measurement="kg",
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="personal_points",
        translation_key="personal_points",
        icon="mdi:star-circle",
        suggested_display_precision=0,
    ),
)

PERIOD_SENSORS = tuple(
    SensorEntityDescription(
        key=f"{period}_{metric}",
        translation_key=f"{period}_{metric}",
        icon=icon,
        native_unit_of_measurement=unit,
        suggested_display_precision=0 if metric == "points" else 1,
    )
    for period in ("daily", "weekly", "monthly")
    for metric, icon, unit in (
        ("drive_score", "mdi:car-speed-limiter", "%"),
        ("consumption", "mdi:lightning-bolt", "kWh/100 km"),
        ("points", "mdi:star-circle", None),
    )
)

POINT_SENSORS = (
    SensorEntityDescription(
        key="account_total_points",
        translation_key="account_total_points",
        icon="mdi:star-circle",
        suggested_display_precision=0,
    ),
    *(
        SensorEntityDescription(
            key=f"recent_{category.lower()}_points",
            translation_key=f"recent_{category.lower()}_points",
            icon="mdi:star-circle",
            suggested_display_precision=0,
        )
        for category in ("DRIVING", "CHARGING", "PARKING", "PERSONAL_CHALLENGE")
    ),
    *(
        SensorEntityDescription(
            key=f"latest_{category}_award",
            translation_key=f"latest_{category}_award",
            icon="mdi:star-circle",
            suggested_display_precision=0,
        )
        for category in ("driving", "charging", "parking")
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: EcoCoachConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Register observed metrics."""
    descriptions = (*SENSORS, *PERIOD_SENSORS, *POINT_SENSORS)
    async_add_entities(EcoCoachSensor(entry.runtime_data, entry, description) for description in descriptions)


class EcoCoachSensor(CoordinatorEntity[EcoCoachCoordinator], SensorEntity):
    """A single personal statistics metric."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: EcoCoachCoordinator, entry: EcoCoachConfigEntry, description: SensorEntityDescription
    ) -> None:
        """Initialize a VIN-scoped sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        key = description.key.removeprefix("personal_")
        self._attr_unique_id = f"{entry.data[CONF_VIN]}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data[CONF_VIN])},
            "name": f"Eco Coach {entry.data[CONF_VIN]}",
            "manufacturer": "Mercedes-Benz",
        }

    @property
    def native_value(self) -> float | None:
        """Return the captured metric or unknown when absent."""
        if self.entity_description.key == "account_total_points":
            return self.coordinator.data.points.total if self.coordinator.data.points is not None else None
        if self.entity_description.key.startswith("latest_"):
            award = self._latest_award()
            return award.points if award else None
        if self.entity_description.key.startswith("recent_"):
            if self.coordinator.data.points is None:
                return None
            category = self.entity_description.key.removeprefix("recent_").removesuffix("_points").upper()
            return self.coordinator.data.points.recent.get(category, 0)
        period, _, metric = self.entity_description.key.partition("_")
        data = getattr(self.coordinator.data, period, None)
        return getattr(data, metric, None)

    def _latest_award(self) -> PointsAward | None:
        category = self.entity_description.key.removeprefix("latest_").removesuffix("_award")
        return self.coordinator.history.latest(category) if self.coordinator.history is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Expose only the time of the most recent award, never trip details."""
        if not self.entity_description.key.startswith("latest_"):
            return None
        award = self._latest_award()
        return {"occurred_at": award.occurred_at.isoformat()} if award else None
