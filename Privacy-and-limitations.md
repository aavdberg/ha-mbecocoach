# Privacy and known limitations

[Home](Home) · [Sign-in](Sign-in) · [Sensors and points](Sensors-and-points)

Mercedes Eco Coach for Home Assistant is **unofficial and experimental**.
It is not affiliated with Mercedes-Benz. Its use depends on an external
Eco Coach account and API, which may change or become unavailable.

## Data stored and exposed

- Home Assistant stores the configured VIN and, for browser or direct
  sign-in, OAuth access and refresh tokens in config entry storage. An
  access-token-only entry stores the manually provided token.
- The direct login method uses a temporary isolated session and does not
  keep the entered username or password after login.
- The integration's private `.storage` history cache contains only award
  IDs, categories, points and occurrence times. Home Assistant's backups
  can contain this cache and tokens, so protect both the configuration
  directory and backups.
- Publicly visible Home Assistant entities show aggregate statistics,
  balances, recent award point values, occurrence times and newly
  received point events. The integration discards trip-level report
  details, messages and competitor data rather than placing them in
  entity attributes.
- Re-import overwrites only this integration's cached awards, not
  Home Assistant recorder history or data owned by another integration.

Home Assistant's own recorder can retain historical states of enabled
entities according to **your** recorder settings. Do not share an
unredacted backup, diagnostics dump, callback URL, access/refresh token,
vehicle VIN or raw response with maintainers or in a public issue.

## Current limitations

- Login with the mobile app's callback requires copying a one-time URL
  in a desktop browser; it is **not** Home Assistant's standard HTTPS
  OAuth redirect. Some browsers may not expose the custom-scheme URL.
- Experimental direct login cannot handle MFA, extra verification or
  unexpected consent screens. Sign in with the account that actually has
  Eco Coach access for the vehicle.
- Automatic renewal is implemented for OAuth entries, but has not been
  verified against a real, naturally expired token. Entries using only
  a manually entered access token have no automatic renewal.
- Levels, challenges, duels, trip-level award details, full trip history,
  reports, coach messages and WebSocket updates are not implemented.
- A large full-history re-import with the extended timeout still awaits
  a real-account retry. A failed import preserves the current cache.
- The card is bundled but must be added manually to a dashboard. The
  integration cannot change the Eco Coach app or your Mercedes account.

Track proposed additions in
[GitHub Issues](https://github.com/aavdberg/ha-mbecocoach/issues).
Never include private account or vehicle data in a feature request.
