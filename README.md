# Mercedes Eco Coach for Home Assistant

[![CI](https://github.com/aavdberg/ha-mbecocoach/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/aavdberg/ha-mbecocoach/actions/workflows/ci.yml)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

An **unofficial, experimental** custom integration for Home Assistant 2026.9
that brings Mercedes Eco Coach driving statistics, points and award history
into Home Assistant. It is not affiliated with Mercedes-Benz.

## Features

- Personal drive score, electric consumption, saved emissions and points;
  daily, weekly and monthly statistics where provided by Eco Coach.
- Account point balance, recent points by category and latest individual awards.
- Locally cached award history with a manual re-import button and paginated
  Home Assistant action. Historical awards are not replayed as new events.
- A bundled, theme-aware Eco Coach dashboard card with selectable statistics
  and browsable award history.

## Requirements

- Home Assistant **2026.9.0 or newer**, HACS (recommended) or manual installation.
- A Mercedes account with Eco Coach access for your vehicle and its 17-character VIN.

## Install via HACS

[![Open the repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=aavdberg&repository=ha-mbecocoach&category=integration)

Until the [HACS default-catalog submission](https://github.com/hacs/default/pull/11495)
is accepted, add `https://github.com/aavdberg/ha-mbecocoach` to **HACS →
Custom repositories** as an **Integration**. Download **Mercedes Eco Coach**
and restart Home Assistant. Alternatively, copy
`custom_components/mbecocoach` from `main` into
`/config/custom_components/` and restart.

Go to **Settings → Devices & services → Add integration → Mercedes Eco Coach**
and enter the VIN. Choose browser-assisted login (default) or the experimental
direct login; an existing access token can also be entered manually. The
browser flow requires a desktop browser and a one-time callback copy. See the
[sign-in guide](https://github.com/aavdberg/ha-mbecocoach/wiki/Sign-in) before
starting. Never share your callback URL, password or tokens.

## Dashboard and documentation

After setup, choose **Edit dashboard → Add card → Eco Coach**, then select your
**Total account points** entity. The card is installed with the integration
but is not automatically added to your dashboards.

The [Wiki](https://github.com/aavdberg/ha-mbecocoach/wiki) covers:
[installation](https://github.com/aavdberg/ha-mbecocoach/wiki/Installation),
[sign-in](https://github.com/aavdberg/ha-mbecocoach/wiki/Sign-in),
[sensors and points](https://github.com/aavdberg/ha-mbecocoach/wiki/Sensors-and-points),
[the dashboard card](https://github.com/aavdberg/ha-mbecocoach/wiki/Dashboard-card),
[troubleshooting](https://github.com/aavdberg/ha-mbecocoach/wiki/Troubleshooting)
and [privacy and limitations](https://github.com/aavdberg/ha-mbecocoach/wiki/Privacy-and-limitations).

This is an experimental integration: direct login does not support MFA or
unexpected consent screens, and token renewal at a real expiry is not yet
confirmed. For problems or feature requests, use
[GitHub Issues](https://github.com/aavdberg/ha-mbecocoach/issues) without
including credentials, callback URLs, VINs, raw logs or private trip data.

Development happens on `dev`; published releases come from `main`.
