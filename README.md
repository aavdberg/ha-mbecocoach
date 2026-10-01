# Mercedes Eco Coach for Home Assistant

Experimental custom integration targeting Home Assistant 2026.9. Based on observed iOS Eco Coach 5.7.0 traffic; **not affiliated with Mercedes-Benz**.

## Current scope

The integration polls the observed `GET /api/v5/{VIN}/statistics/personal` endpoint every 15 minutes. It exposes drive score, average consumption, and saved emissions, **only when the endpoint returns those numeric fields**. Units and semantics for these metrics have not been independently verified, so no units are assigned. Missing fields appear as unknown. Each configured VIN has its own device.

**Important limitations:** The observed host (`ecocoach.query.api.dvb.corpinter.net`) appears to be an internal hostname and may not resolve from Home Assistant. Live connectivity and use of the Mercedes token with this endpoint have not been verified. The Mercedes Identity Platform login flow and token refresh are not documented sufficiently to implement safely. You must supply an existing bearer token from an authorized session and replace it through reauthentication when it expires. If the host is not reachable or does not accept that token, setup cannot succeed. Do not publish tokens or captures.

Points, levels, challenges, duels, activity history, weekly reports, coach events, services, and WebSocket updates **are not implemented**. Their endpoints and response formats require further capture-based investigation; example values in the research notes are not live API schemas.

## Install and configure

Add `https://github.com/aavdberg/ha-mbecocoach` as a custom integration repository in HACS, or copy `custom_components/mbecocoach` into your Home Assistant `config/custom_components` folder, then restart Home Assistant. Under **Settings → Devices & services → Add integration**, select **Mercedes Eco Coach**. Provide your 17-character VIN and an authorized Eco Coach bearer token (without the `Bearer ` prefix). Configuration tests the observed statistics endpoint before creating the entry. A rejected token triggers the Home Assistant reauthentication flow.

The token is stored in Home Assistant's config entry storage and is never written to logs by this integration. The host is fixed; arbitrary user-supplied endpoints are deliberately not accepted. No real Mercedes credentials are required by repository tests.

## Development

Create an issue before implementing a new feature or bug fix. Run `ruff check custom_components tests`, `ruff format --check custom_components tests`, and `python -m pytest -q`. GitHub Actions also runs hassfest, HACS validation, and secret scanning. Development belongs on `dev`; promote to `main` only when explicitly requested. See [issue #1](https://github.com/aavdberg/ha-mbecocoach/issues/1) for verified facts and remaining investigation.
