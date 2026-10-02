# Eco Coach dashboard card

[Home](Home) · [Installation](Installation) · [Sensors and points](Sensors-and-points)

The integration bundles an original, theme-aware Lovelace card. It loads
automatically with an active Eco Coach integration, but **does not modify
your dashboards** and does not use Mercedes-Benz artwork or copied app
assets.

## Add the card

1. Install the integration, add a vehicle and restart Home Assistant.
2. Reload your browser dashboard. Select **Edit dashboard → Add card →
   Eco Coach**.
3. In the card editor, choose the **Total account points** sensor for
   the vehicle you want to display, then save. To show another vehicle,
   add a second card and select its total-points sensor.

If you added the card before completing setup, open its editor afterward
and select a vehicle's total-points sensor. If the card is missing, confirm
that the integration has an active entry, restart Home Assistant and
reload the dashboard browser tab.

## What the card shows

- The account-point banner shows the account's available total balance.
  Select it to jump to the award list.
- The four point categories (driving, charging, parking and personal
  challenge) cover a rolling **last seven days** period, not the entire
  account history.
- Personal drive score, average consumption and saved emissions come
  from the current local Monday–Sunday calendar week request.
- Daily, weekly and monthly statistics are provider-defined summaries;
  they are not calculated by adding the other tiles.
- Selecting a statistic tile opens that sensor's Home Assistant details,
  including any recorded history available in your Home Assistant instance.

The award list displays eight cached awards at a time. Use **Next** and
**Previous** to browse; simply paging never calls the expensive full
re-import. The card refreshes a small history page when relevant point
entities change. Individual awards do not open trip-level details.

**Re-import history** explicitly fetches the full available history and
replaces only Eco Coach's local cache. It can take longer than ordinary
polling. If the remote API times out or cannot be reached, existing
awards remain visible, and the card shows an error. A missing or disabled
button is reported separately from a remote failure.

The card supports keyboard operation and preserves focus when navigating
or using re-import. It uses your Home Assistant theme. If you disable the
integration, its card module is not loaded until an entry is enabled again.
