"""Manual, privacy-limited re-import of Eco Coach point history."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EcoCoachConfigEntry
from .const import CONF_VIN, DOMAIN
from .coordinator import EcoCoachCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: EcoCoachConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Provide an explicit manual re-import for this configured vehicle."""
    async_add_entities([EcoCoachHistoryButton(entry.runtime_data, entry)])


class EcoCoachHistoryButton(CoordinatorEntity[EcoCoachCoordinator], ButtonEntity):
    """Overwrite only the locally cached Eco Coach award list."""

    _attr_has_entity_name = True
    _attr_translation_key = "refresh_points_history"
    _attr_icon = "mdi:history"

    def __init__(self, coordinator: EcoCoachCoordinator, entry: EcoCoachConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.data[CONF_VIN]}_refresh_points_history"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data[CONF_VIN])},
            "name": f"Eco Coach {entry.data[CONF_VIN]}",
            "manufacturer": "Mercedes-Benz",
        }

    async def async_press(self) -> None:
        """Fetch all existing awards and atomically replace the integration cache."""
        await self.coordinator.async_replace_history()
