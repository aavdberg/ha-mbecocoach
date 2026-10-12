"""Minimal private points archive in Home Assistant's local storage."""

from __future__ import annotations

from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .api import (
    DriveDetails,
    EcoCoachError,
    PointsAward,
    drive_details_to_storage,
    parse_stored_drive_details,
)


class PointsHistory:
    """Persist awards and a minimal, location-free driving summary per entry."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict] = Store(hass, 1, f"mbecocoach_points_{entry_id}", private=True)
        self._awards: dict[str, PointsAward] = {}

    @property
    def count(self) -> int:
        return len(self._awards)

    def latest(self, category: str) -> PointsAward | None:
        """Return the newest award for a category, including imported history."""
        return max(
            (award for award in self._awards.values() if award.category == category),
            key=lambda award: award.occurred_at,
            default=None,
        )

    async def async_load(self) -> bool:
        """Return false when no archive exists; reject corrupted data."""
        data = await self._store.async_load()
        if data is None:
            return False
        if not isinstance(data, dict) or not isinstance(data.get("awards"), list):
            raise EcoCoachError("Saved points history is invalid")
        loaded: dict[str, PointsAward] = {}
        for record in data["awards"]:
            base_fields = {"id", "category", "points", "occurred_at"}
            if not isinstance(record, dict) or set(record) not in (base_fields, base_fields | {"drive_details"}):
                raise EcoCoachError("Saved points history contains an invalid award")
            try:
                occurred_at = datetime.fromisoformat(record["occurred_at"])
            except (TypeError, ValueError) as err:
                raise EcoCoachError("Saved points history contains an invalid date") from err
            if (
                not isinstance(record["id"], str)
                or not record["id"]
                or record["id"] in loaded
                or record["category"] not in ("driving", "charging", "parking")
                or isinstance(record["points"], bool)
                or not isinstance(record["points"], int)
                or record["points"] < 0
                or occurred_at.tzinfo is None
            ):
                raise EcoCoachError("Saved points history contains an invalid award")
            details = None
            if "drive_details" in record:
                if record["category"] != "driving":
                    raise EcoCoachError("Saved points history contains details for a non-driving award")
                details = parse_stored_drive_details(record["drive_details"])
            loaded[record["id"]] = PointsAward(record["id"], record["category"], record["points"], occurred_at, details)
        self._awards = loaded
        return True

    async def async_replace(self, awards: tuple[PointsAward, ...]) -> None:
        """Replace only our own history after a successful complete API response."""
        await self._save({award.id: award for award in awards})

    async def async_merge(self, awards: tuple[PointsAward, ...]) -> None:
        """Add awards and enrich existing entries when confirmed details arrive."""
        updates = {}
        for award in awards:
            existing = self._awards.get(award.id)
            if existing is not None:
                old_details = existing.drive_details
                new_details = award.drive_details
                if old_details is not None and new_details is not None:
                    details = DriveDetails(
                        new_details.drive_score if new_details.drive_score is not None else old_details.drive_score,
                        new_details.distance_km if new_details.distance_km is not None else old_details.distance_km,
                        new_details.electric_consumption
                        if new_details.electric_consumption is not None
                        else old_details.electric_consumption,
                        new_details.co2_emissions_kg
                        if new_details.co2_emissions_kg is not None
                        else old_details.co2_emissions_kg,
                        new_details.duration_seconds
                        if new_details.duration_seconds is not None
                        else old_details.duration_seconds,
                        new_details.start_time if new_details.start_time is not None else old_details.start_time,
                        new_details.temperature_c
                        if new_details.temperature_c is not None
                        else old_details.temperature_c,
                        new_details.battery_percent_change
                        if new_details.battery_percent_change is not None
                        else old_details.battery_percent_change,
                    )
                else:
                    details = new_details or old_details
                award = PointsAward(award.id, award.category, award.points, award.occurred_at, details)
            if existing != award:
                updates[award.id] = award
        if updates:
            await self._save({**self._awards, **updates})

    async def _save(self, awards: dict[str, PointsAward]) -> None:
        def record(award: PointsAward) -> dict:
            saved = {
                "id": award.id,
                "category": award.category,
                "points": award.points,
                "occurred_at": award.occurred_at.isoformat(),
            }
            if award.drive_details is not None:
                saved["drive_details"] = drive_details_to_storage(award.drive_details)
            return saved

        await self._store.async_save({"awards": [record(award) for award in awards.values()]})
        self._awards = awards

    def page(self, offset: int, limit: int) -> dict:
        """Return a bounded history page without IDs, routes or coaching messages."""
        ordered = sorted(self._awards.values(), key=lambda award: award.occurred_at, reverse=True)
        page = []
        for award in ordered[offset : offset + limit]:
            item = {
                "category": award.category,
                "points": award.points,
                "occurred_at": award.occurred_at.isoformat(),
            }
            if award.drive_details is not None:
                item["drive_details"] = drive_details_to_storage(award.drive_details)
            page.append(item)
        return {
            "total": len(ordered),
            "offset": offset,
            "awards": page,
        }
