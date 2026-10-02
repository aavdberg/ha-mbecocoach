# Mercedes Eco Coach for Home Assistant

Experimental Home Assistant 2026.9 custom integration. Not affiliated with Mercedes-Benz. Development lives on `dev`; `main` is not released.

## Install and test

Copy `custom_components/mbecocoach` from the **`dev` branch** to your Home Assistant `config/custom_components` folder and restart Home Assistant. The test Home Assistant already has the development version installed. Select **Mercedes Eco Coach** under **Settings → Devices & services → Add integration**.

Enter your 17-character VIN and **leave the optional bearer token blank** to try browser-assisted Mercedes login:

1. Copy the authorization URL displayed by Home Assistant into a **desktop browser without the Eco Coach mobile app installed**. Do not use your iPhone for this step.
2. Sign in to Mercedes Identity in that browser. The registered `ecocoach://login/callback` link may produce a browser error because no desktop app handles it. Copy the **complete callback URL**, including query parameters, from the address bar or browser history.
3. Within ten minutes, paste it into the Home Assistant form. Never share this URL: it contains a short-lived one-time code. Home Assistant validates the PKCE state, exchanges the code and verifies the Eco Coach statistics endpoints before saving tokens.

**The browser-assisted callback has not yet been verified with a real account.** Some browsers may not expose the failed custom-protocol redirect; if it cannot be copied, the flow cannot finish. Do not send a callback URL, password or access/refresh token to this repository or chat. Alternatively, supply an existing Eco Coach bearer access token in the optional field; that legacy mode cannot renew tokens automatically.

OAuth entries store access and refresh tokens in Home Assistant's config entry storage and renew them before expiration. Secure the storage and backups. If renewal fails, Home Assistant requests reauthentication. In that form, leave the token blank to try a fresh browser login or supply a replacement access token.

## Data

The integration polls the observed `/api/v5/{VIN}/statistics/personal` and `/api/v5/{VIN}/statistics/all` endpoints every 15 minutes. It exposes personal drive score (%), average electric consumption (kWh/100 km), saved emissions (kg), plus daily, weekly and monthly drive score, electric consumption and points where present. The personal request uses the current and preceding Monday-Sunday calendar weeks in Home Assistant's configured time zone. Missing metrics remain unknown. Trip, message and chart details are not persisted.

The 2026-10-02 iOS capture confirmed the public Eco Coach OAuth client ID `022bed8c-3a28-4b1d-b465-9ca0f406b34e`, redirect URI `ecocoach://login/callback`, scopes `openid offline_access email phone profile ciam-uid`, and PKCE `S256`. Home Assistant generates a new random verifier and state for each login. The authorization URL reaches the Mercedes CIAM login page without credentials; completing the handoff from a desktop browser still needs user testing. Unlike [MercedesME 2020](https://github.com/ReneNulschDE/mbapi2020), this integration does not request or store a Mercedes password.

Lifetime points, levels, challenges, duels, activity history, reports, coach events, services and WebSocket updates remain unimplemented. Captured `/api/v5/user/points` and `/api/v5/{VIN}/report` responses have those summaries and potentially sensitive details; see [issue #3](https://github.com/aavdberg/ha-mbecocoach/issues/3). Static Android APK route strings for trends, energy history, transactions and event details are not proof of working HTTP requests.

## Development

Create a detailed English issue for each feature or bug. Run `ruff check custom_components tests`, `ruff format --check custom_components tests` and `python -m pytest -q`. GitHub CI also runs hassfest, HACS validation and secret scanning. Never commit tokens, callback URLs, VINs, real trip data or raw captures. Promote `dev` to `main` only when explicitly requested.
