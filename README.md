# Mercedes Eco Coach for Home Assistant

Experimental custom integration targeting Home Assistant 2026.9. Based on observed iOS Eco Coach 5.7.0 traffic; **not affiliated with Mercedes-Benz**.

## Current scope

The integration polls the observed `GET /api/v5/{VIN}/statistics/personal` and `GET /api/v5/{VIN}/statistics/all` endpoints every 15 minutes. Personal statistics cover the current Monday-Sunday calendar week compared to the preceding week, using Home Assistant's configured time zone. Sensors show personal drive score (%), average electric consumption (kWh/100 km), and saved emissions (kg) when their captured icon/unit combinations are present. Period summaries show daily, weekly, and monthly drive score (%), electric consumption (kWh/100 km), and points where returned in the captured aggregate schema. Missing metrics appear as unknown. Each configured VIN has its own device; private trip and message data is not stored.

**Important limitations:** The observed host (`ecocoach.query.api.dvb.corpinter.net`) is reachable in the test environment and answered the app's authenticated requests with HTTP 200; connectivity from your Home Assistant installation has not been verified. The capture confirms that an OAuth refresh request at `id.mercedes-benz.com/as/token.oauth2` returns the access token used by the Eco Coach API, but does not establish a safe initial login flow for Home Assistant. **Home Assistant login with a Mercedes username/password or automatic token renewal is not supported.** You must supply an existing bearer access token from an authorized session and replace it through reauthentication when it expires. Do not give the token to third parties or paste it into an issue. If the host is not reachable or does not accept that token, setup cannot succeed.

Lifetime points, levels, challenges, duels, activity history, historical weekly reports, coach events, services, and WebSocket updates **are not implemented**. The iOS capture also shows `/api/v5/user/points` and `/api/v5/{VIN}/report` with lifetime points, level, events, challenges and messages. These need separate privacy-conscious mapping and test coverage before they become Home Assistant entities; see [issue #3](https://github.com/aavdberg/ha-mbecocoach/issues/3).

Static inspection of the Android 5.7.0 APK additionally found route templates for `statistics/trends`, `user/transactions`, `energy/history`, and `{vin}/events/{eventId}`. These are **not confirmed working requests**: their HTTP methods, parameters, and response schemas still need to be verified without exposing personal data. See [issue #3](https://github.com/aavdberg/ha-mbecocoach/issues/3) for the evidence and follow-up scope.

## Install and configure

For this unreleased development version, copy `custom_components/mbecocoach` **from the `dev` branch** into your Home Assistant `config/custom_components` folder, then restart Home Assistant. HACS installation will be available after an explicit release on `main`; the default branch does not yet contain the integration. Under **Settings → Devices & services → Add integration**, select **Mercedes Eco Coach**. Provide your 17-character VIN and an authorized Eco Coach bearer token (without the `Bearer ` prefix). Configuration tests the observed statistics endpoint before creating the entry. A rejected token triggers the Home Assistant reauthentication flow.

The token is stored in Home Assistant's config entry storage and is never written to logs by this integration. The host is fixed; arbitrary user-supplied endpoints are deliberately not accepted. No real Mercedes credentials are required by repository tests. Setup verifies the personal statistics call; startup also requires the `statistics/all` call to succeed, so errors in either endpoint are surfaced instead of creating partial-looking sensors.

## Development

Create an issue before implementing a new feature or bug fix. Run `ruff check custom_components tests`, `ruff format --check custom_components tests`, and `python -m pytest -q`. GitHub Actions also runs hassfest, HACS validation, and secret scanning. Development belongs on `dev`; promote to `main` only when explicitly requested. See [issue #1](https://github.com/aavdberg/ha-mbecocoach/issues/1) for verified facts and remaining investigation.
