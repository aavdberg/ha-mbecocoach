# Mercedes Eco Coach for Home Assistant

Welcome to the user guide for the **unofficial, experimental** Mercedes Eco
Coach integration for Home Assistant 2026.9 and newer. It is not affiliated
with Mercedes-Benz.

With an Eco Coach-enabled Mercedes account, the integration shows driving
statistics, an account point balance, recent point awards and a dashboard card.
It can also keep a private local cache of the available award history.

## Start here

1. [Install the integration](Installation) through HACS as a custom repository
   or copy its component directory manually.
2. [Sign in](Sign-in) with the Mercedes account that has Eco Coach access to
   your vehicle. You will need its 17-character VIN.
3. [Understand your sensors and points](Sensors-and-points), including the
   different time periods and the optional history re-import.
4. [Add the Eco Coach dashboard card](Dashboard-card) to a dashboard.

For errors, read [Troubleshooting](Troubleshooting). For what is stored
locally, what is not exposed, and known limitations, read
[Privacy and limitations](Privacy-and-limitations).

The project lives at [aavdberg/ha-mbecocoach](https://github.com/aavdberg/ha-mbecocoach).
Until the [HACS default-catalog submission](https://github.com/hacs/default/pull/11495)
is accepted, add it as a **custom repository** in HACS; it is not yet
searchable as a default HACS integration.

> Never publish passwords, tokens, callback URLs, vehicle VINs, raw Home
> Assistant logs or personal Eco Coach data in issues or discussions.
