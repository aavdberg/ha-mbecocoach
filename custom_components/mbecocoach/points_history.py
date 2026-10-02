"""Minimal private points archive in Home Assistant's local storage."""

from __future__ import annotations

from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .api import EcoCoachError, PointsAward


class PointsHistory:
    """Persist only award identity, category, points and timestamp per entry."""

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
            if not isinstance(record, dict) or set(record) != {"id", "category", "points", "occurred_at"}:
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
            loaded[record["id"]] = PointsAward(record["id"], record["category"], record["points"], occurred_at)
        self._awards = loaded
        return True

    async def async_replace(self, awards: tuple[PointsAward, ...]) -> None:
        """Replace only our own history after a successful complete API response."""
        await self._save({award.id: award for award in awards})

    async def async_merge(self, awards: tuple[PointsAward, ...]) -> None:
        """Add newly observed awards without rewriting on every poll."""
        additions = {award.id: award for award in awards if award.id not in self._awards}
        if additions:
            await self._save({**self._awards, **additions})

    async def _save(self, awards: dict[str, PointsAward]) -> None:
        await self._store.async_save(
            {
                "awards": [
                    {
                        "id": award.id,
                        "category": award.category,
                        "points": award.points,
                        "occurred_at": award.occurred_at.isoformat(),
                    }
                    for award in awards.values()
                ]
            }
        )
        self._awards = awards

    def page(self, offset: int, limit: int) -> dict:
        """Return a bounded history page without internal IDs or trip details."""
        ordered = sorted(self._awards.values(), key=lambda award: award.occurred_at, reverse=True)
        return {
            "total": len(ordered),
            "offset": offset,
            "awards": [
                {"category": award.category, "points": award.points, "occurred_at": award.occurred_at.isoformat()}
                for award in ordered[offset : offset + limit]
            ],
        }
