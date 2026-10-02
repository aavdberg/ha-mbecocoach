# Sensors, point awards and history

[Home](Home) · [Dashboard card](Dashboard-card) · [Privacy](Privacy-and-limitations)

The integration polls the Eco Coach API about every **15 minutes**. Sensors
belong to the Eco Coach device for the configured vehicle. Missing data is
shown as unknown rather than invented. Home Assistant suggests display
precision (one decimal for scores and consumption, two for saved emissions,
whole numbers for points) without changing numeric values used by
automations.

## Driving statistics

| Sensor group | Metrics | Period |
| --- | --- | --- |
| Personal | Drive score (%), average electric consumption (kWh/100 km), saved emissions (kg), personal period points | Current local Monday–Sunday calendar week requested by the integration; the request also includes the preceding week |
| Daily, weekly and monthly | Drive score, electric consumption and points where available | Provider-defined aggregates for the named period; exact boundaries may differ from the personal week |

**Personal period points are not the account's total point balance.** Do
not add daily/weekly/monthly values to derive a lifetime total.

## Account points and award sensors

- **Total account points** is the available account balance. Select this
  sensor in the dashboard card editor.
- **Recent driving, charging, parking and personal challenge points**
  represent points earned in a rolling **last seven days** period.
  Their sum is not necessarily the lifetime balance.
- **Latest driving, charging and parking award** sensors contain an award
  point value and its occurrence time. They do not contain trip details.
- The **Points awarded** event entity emits newly seen driving, charging
  and parking awards after integration startup. Historical awards are
  **not replayed** into Home Assistant as if they happened now. Award IDs
  already seen remain remembered while that event entity is running.

## Local award history

At first setup the integration requests available historical awards once
and stores **only award ID, category, point value and occurrence time** in
Home Assistant's private `.storage`. Subsequent polls merge recent awards.
If the optional first full-history request temporarily fails, setup can
continue with already fetched recent awards. An authentication failure
still requires reauthentication.

To fetch all available history again, press the **Re-import point history**
button on the Eco Coach device, or use the card's **Re-import history**
control. Re-import can take longer than a regular poll; it replaces
**only the integration's local award cache**, not Home Assistant recorder
history, unrelated devices, or other integrations' data. A failed re-import
leaves the existing cache intact. Do not press it repeatedly during
connectivity issues.

To browse awards, use the [dashboard card](Dashboard-card) or call the
response-producing Home Assistant action
`mbecocoach.get_points_history` from **Developer Tools → Actions**:

| Field | Purpose |
| --- | --- |
| `entry_id` (required) | Select the Eco Coach integration entry for the vehicle |
| `offset` (optional) | Number of newest-first awards to skip; default 0 |
| `limit` (optional) | Page size from 1 to 100; default 50 |

The response contains a total count and a newest-first page with category,
points and time. Avoid placing the entire history in sensor attributes.
Per-award trip details, messages and competitor information are not exposed.
