"""Observed Eco Coach personal statistics as Home Assistant sensors."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EcoCoachConfigEntry
from .const import CONF_VIN, DOMAIN
from .coordinator import EcoCoachCoordinator

SENSORS = (
    SensorEntityDescription(
        key="personal_drive_score",
        translation_key="drive_score",
        icon="mdi:car-speed-limiter",
        native_unit_of_measurement="%",
    ),
    SensorEntityDescription(
        key="personal_avg_consumption",
        translation_key="avg_consumption",
        icon="mdi:lightning-bolt",
        native_unit_of_measurement="kWh/100 km",
    ),
    SensorEntityDescription(
        key="personal_saved_emissions",
        translation_key="saved_emissions",
        icon="mdi:leaf",
        native_unit_of_measurement="kg",
    ),
    SensorEntityDescription(
        key="personal_points",
        translation_key="personal_points",
        icon="mdi:star-circle",
    ),
)

PERIOD_SENSORS = tuple(
    SensorEntityDescription(
        key=f"{period}_{metric}",
        translation_key=f"{period}_{metric}",
        icon=icon,
        native_unit_of_measurement=unit,
    )
    for period in ("daily", "weekly", "monthly")
    for metric, icon, unit in (
        ("drive_score", "mdi:car-speed-limiter", "%"),
        ("consumption", "mdi:lightning-bolt", "kWh/100 km"),
        ("points", "mdi:star-circle", None),
    )
)


async def async_setup_entry(
    hass: HomeAssistant, entry: EcoCoachConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Register observed metrics."""
    descriptions = (*SENSORS, *PERIOD_SENSORS)
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
        period, _, metric = self.entity_description.key.partition("_")
        data = getattr(self.coordinator.data, period, None)
        return getattr(data, metric, None)
