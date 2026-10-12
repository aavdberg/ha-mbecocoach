---
applyTo: "custom_components/mbecocoach/**,tests/**"
---

# Mercedes Eco Coach implementation context

Use the repository-wide development/review/release rules. This is a cloud
integration, not BLE; do not copy Petkit protocol, device or Python assumptions.
Target Python 3.14 and Home Assistant 2026.9.

## Verified architecture

- `__init__.py` stores `EcoCoachCoordinator` in `entry.runtime_data`, forwards
  sensor/event/button platforms, registers the static frontend route once and
  loads the card only while entries are enabled. Unload removes the shared
  service/card registration after the last enabled entry.
- `api.py` implements `EcoCoachClient`, typed statistics/award data and defensive
  parsers for observed nested cards. Do not treat statistics as flat metrics.
- `coordinator.py` polls every 15 minutes, renews OAuth tokens before expiry,
  updates config-entry tokens and distinguishes `ConfigEntryAuthFailed` from
  `UpdateFailed`. The history lock serializes cache merge/re-import operations.
- `config_flow.py`, `oauth.py` and `direct_login.py` handle browser PKCE,
  optional direct login, manual tokens and reauthentication. Direct login does
  not persist passwords and cannot guarantee MFA/consent support. Live initial
  login succeeded; live refresh-token expiry/rotation remains unverified.
- `points_history.py` uses private local HA storage per entry, caching only
  award metadata and a strict location-free driving-summary whitelist.
  Re-import replaces this cache, not HA recorder history. Failed imports must
  preserve the existing cache.
- `sensor.py`, `event.py`, `button.py` use coordinator-backed entities with
  stable unique IDs and translated names. Events do not replay imported history
  into the recorder or emit the same award again after a temporary disappearance.
- `frontend/mbecocoach-card.js` is original HA-themed UI; no copied Mercedes
  artwork. The paginated `mbecocoach.get_points_history` response service is
  entry-scoped with an offset and a limit of 1-100.

## Evidence, semantics and privacy

Only the observed `/api/v5/{VIN}/statistics/personal`, `/statistics/all`,
`/report` and `/api/v5/user/points` behavior is evidence for implementation.
Static APK strings alone do not prove HTTP behavior.
Personal period points are not total account points. Category breakdowns use
the last seven days; personal statistics use local Monday-Sunday weeks.
Daily/weekly/monthly aggregates have provider-defined boundaries.
Missing metrics remain unknown, not zero. Never add inferred metrics,
unverified CO2 semantics, routes, locations or raw response attributes.

Never expose credentials, tokens, callbacks, identifiers, raw captures or trip
details in logs, fixtures, issues or review comments. Use only synthetic data.
Preserve redacted stage/status logging and explicit repository-standard errors.

When adding entities, use existing description/coordinator patterns and stable
English keys. Update `strings.json` first and mirror keys in all translations.
Add synthetic parser/coordinator/entity/flow tests as applicable, plus the
existing Node card tests for UI changes. Keep test data and shared mocks isolated.
