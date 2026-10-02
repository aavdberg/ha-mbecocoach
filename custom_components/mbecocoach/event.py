"""Individual Eco Coach points awarded since this integration started."""

from __future__ import annotations

from typing import ClassVar

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EcoCoachConfigEntry
from .const import CONF_VIN, DOMAIN
from .coordinator import EcoCoachCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: EcoCoachConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add an event history for new vehicle point awards."""
    async_add_entities([EcoCoachPointsEvent(entry.runtime_data, entry)])


class EcoCoachPointsEvent(CoordinatorEntity[EcoCoachCoordinator], EventEntity):
    """Publish only new point awards, not private trip/report content."""

    _attr_has_entity_name = True
    _attr_translation_key = "points_awarded"
    _attr_event_types: ClassVar[list[str]] = ["driving", "charging", "parking"]
    _attr_icon = "mdi:star-circle"

    def __init__(self, coordinator: EcoCoachCoordinator, entry: EcoCoachConfigEntry) -> None:
        """Keep seen IDs only in memory and scope the entity to the vehicle."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.data[CONF_VIN]}_points_awarded"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data[CONF_VIN])},
            "name": f"Eco Coach {entry.data[CONF_VIN]}",
            "manufacturer": "Mercedes-Benz",
        }
        self._seen_ids = {award.id for award in coordinator.data.awards}

    def _handle_coordinator_update(self) -> None:
        """Publish later awards once; do not backfill historical private activity."""
        awards = self.coordinator.data.awards
        current_ids = {award.id for award in awards}
        emitted = False
        for award in sorted(awards, key=lambda item: item.occurred_at):
            if award.id not in self._seen_ids:
                self._trigger_event(
                    award.category, {"points": award.points, "occurred_at": award.occurred_at.isoformat()}
                )
                self.async_write_ha_state()
                emitted = True
        self._seen_ids.update(current_ids)
        if not emitted:
            super()._handle_coordinator_update()
