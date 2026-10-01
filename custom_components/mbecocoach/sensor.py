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
    SensorEntityDescription(key="drive_score", translation_key="drive_score", icon="mdi:car-speed-limiter"),
    SensorEntityDescription(
        key="avg_consumption",
        translation_key="avg_consumption",
        icon="mdi:lightning-bolt",
    ),
    SensorEntityDescription(
        key="saved_emissions",
        translation_key="saved_emissions",
        icon="mdi:leaf",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: EcoCoachConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Register observed metrics."""
    async_add_entities(EcoCoachSensor(entry.runtime_data, entry, description) for description in SENSORS)


class EcoCoachSensor(CoordinatorEntity[EcoCoachCoordinator], SensorEntity):
    """A single personal statistics metric."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: EcoCoachCoordinator, entry: EcoCoachConfigEntry, description: SensorEntityDescription
    ) -> None:
        """Initialize a VIN-scoped sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.data[CONF_VIN]}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data[CONF_VIN])},
            "name": f"Eco Coach {entry.data[CONF_VIN]}",
            "manufacturer": "Mercedes-Benz",
        }

    @property
    def native_value(self) -> float | None:
        """Return the captured metric or unknown when absent."""
        return getattr(self.coordinator.data, self.entity_description.key, None)
