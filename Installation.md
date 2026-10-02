# Installation

[Home](Home) · [Sign-in](Sign-in) · [Troubleshooting](Troubleshooting)

## Before you begin

- Home Assistant **2026.9.0 or newer**.
- A Mercedes account that can access Eco Coach for the vehicle.
- The vehicle's **17-character VIN** (enter it only in your own Home
  Assistant instance).
- HACS for the recommended installation method.

This is an unofficial, experimental integration. HACS default-catalog
inclusion is [under review](https://github.com/hacs/default/pull/11495);
until it is merged, install from the custom repository.

## Install through HACS (recommended)

1. Open HACS in Home Assistant, then **Custom repositories** from its
   three-dot menu.
2. Enter `https://github.com/aavdberg/ha-mbecocoach` and choose category
   **Integration**.
3. Open **Mercedes Eco Coach** in HACS and download a published release.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration**, search for
   **Mercedes Eco Coach**, and follow the [sign-in guide](Sign-in).

You can also open the
[HACS repository link](https://my.home-assistant.io/redirect/hacs_repository/?owner=aavdberg&repository=ha-mbecocoach&category=integration)
from a browser connected to your Home Assistant instance.

## Install manually

1. Download the latest published release from
   [GitHub](https://github.com/aavdberg/ha-mbecocoach/releases).
2. Copy the **entire** `custom_components/mbecocoach` directory to
   `/config/custom_components/mbecocoach` on your Home Assistant host.
   Keep its `frontend/` and `brand/` directories inside it.
3. Restart Home Assistant and add the integration as described above.

For later updates, replace that directory with the version from the new
release and restart Home Assistant. Keep the private Home Assistant
configuration and its backups secure.

## After installation

Each configured vehicle is represented by an Eco Coach device with sensors,
an event entity and a history re-import button. The optional
[dashboard card](Dashboard-card) is bundled and registered automatically
when the integration is loaded, but you must add it to your dashboard.
If it does not appear after an update, restart Home Assistant and reload
your browser dashboard.

For development testing, the `dev` branch may differ from published releases
on `main`; ordinary users should use a release.
