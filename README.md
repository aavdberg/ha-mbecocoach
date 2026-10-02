# Mercedes Eco Coach for Home Assistant

Experimental Home Assistant 2026.9 custom integration. Not affiliated with Mercedes-Benz. Development lives on `dev`; `main` is not released.

## Install and test

Copy `custom_components/mbecocoach` from the **`dev` branch** to your Home Assistant `config/custom_components` folder and restart Home Assistant. The test Home Assistant already has the development version installed. Select **Mercedes Eco Coach** under **Settings → Devices & services → Add integration**.

Enter your 17-character VIN and **leave the optional bearer token blank** to try browser-assisted Mercedes login:

1. Copy the **prefilled authorization URL field above `callback_url`** into a **desktop browser without the Eco Coach mobile app installed**. Home Assistant does not open the browser automatically. Do not use your iPhone for this step.
2. Sign in to Mercedes Identity in that browser. The registered `ecocoach://login/callback` link may produce a browser error because no desktop app handles it. Copy the **complete callback URL**, including query parameters, from the address bar or browser history.
3. Within ten minutes, paste it into the Home Assistant form. Never share this URL: it contains a short-lived one-time code. Home Assistant validates the PKCE state, exchanges the code and verifies the Eco Coach statistics endpoints before saving tokens.

**Browser-assisted login was confirmed in test Home Assistant with a real account**, including the first statistics update. In Edge, the failed `ecocoach://` launch appeared in the browser developer console rather than the address bar. Copy the callback only into the local Home Assistant form; some browsers may not expose it at all. Do not send a callback URL, password or access/refresh token to this repository or chat. Alternatively, supply an existing Eco Coach bearer access token in the optional field; that legacy mode cannot renew tokens automatically.

**Experimental no-copy alternative:** On the initial VIN form, choose `direct` and leave the optional access token empty. Enter your Mercedes account email/phone and password in the next Home Assistant form. The integration makes a one-time login attempt using the Eco Coach client and an isolated CIAM cookie session, extracts the code from the app's registered redirect internally, then discards the password and session. Only OAuth tokens are stored after vehicle statistics have been verified. **Direct setup succeeded in test Home Assistant with an Eco Coach account authorized for the selected vehicle**; a different Mercedes account completed OAuth but received HTTP 404 for that vehicle's personal statistics. Use the account associated with the vehicle in Eco Coach. This route cannot complete MFA or additional verification/consent screens; use the confirmed browser flow instead if it fails. The Home Assistant log identifies failed stages and HTTP status codes without recording credentials or response bodies. If statistics verification fails, do not repeatedly submit your password. Never share credentials in issues or chat. Reauthentication also offers `direct` while retaining the browser and manual-token options.

OAuth entries store access and refresh tokens in Home Assistant's config entry storage and renew them before expiration. Secure the storage and backups. If renewal fails, Home Assistant requests reauthentication. In that form, leave the token blank to try a fresh browser login or supply a replacement access token.

## Data

The integration polls the observed `/api/v5/{VIN}/statistics/personal` and `/api/v5/{VIN}/statistics/all` endpoints every 15 minutes. It exposes personal drive score (%), average electric consumption (kWh/100 km), saved emissions (kg), **personal period points** from `pointsSummary.sum.points`, plus daily, weekly and monthly drive score, electric consumption and points where present. Personal period points are **not lifetime account points**. The personal request uses the current and preceding Monday-Sunday calendar weeks in Home Assistant's configured time zone. Missing metrics remain unknown. Trip, message and chart details are not persisted.

The 2026-10-02 iOS capture confirmed the public Eco Coach OAuth client ID `022bed8c-3a28-4b1d-b465-9ca0f406b34e`, redirect URI `ecocoach://login/callback`, scopes `openid offline_access email phone profile ciam-uid`, and PKCE `S256`. Home Assistant generates a new random verifier and state for each login. The authorization URL reaches the Mercedes CIAM login page and a user completed the handoff in test Home Assistant. Browser login does not ask Home Assistant for a Mercedes password; the optional experimental direct login does, but never stores it. Automatic token renewal remains unverified against a live expiry.

Lifetime points, levels, challenges, duels, activity history, reports, coach events, services and WebSocket updates remain unimplemented. Captured `/api/v5/user/points` and `/api/v5/{VIN}/report` responses have those summaries and potentially sensitive details; their `from` query range needs further verification before polling them; see [issue #3](https://github.com/aavdberg/ha-mbecocoach/issues/3). Static Android APK route strings for trends, energy history, transactions and event details are not proof of working HTTP requests.

## Development

Create a detailed English issue for each feature or bug. Run `ruff check custom_components tests`, `ruff format --check custom_components tests` and `python -m pytest -q`. GitHub CI also runs hassfest, HACS validation and secret scanning. Never commit tokens, callback URLs, VINs, real trip data or raw captures. Promote `dev` to `main` only when explicitly requested.

For private test-HA troubleshooting, set `logger: {logs: {custom_components.mbecocoach: debug}}` in Home Assistant configuration and restart. Debug messages record only fixed login-stage names, statistics endpoint names (`personal` or `all`) and numeric HTTP status codes; never publish full HA logs or enable HTTP client wire logging, which can expose authorization material. Remove the temporary debug setting when troubleshooting is finished.
