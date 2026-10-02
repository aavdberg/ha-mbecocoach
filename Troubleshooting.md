# Troubleshooting

[Home](Home) · [Sign-in](Sign-in) · [Privacy](Privacy-and-limitations)

| Symptom | What to check |
| --- | --- |
| Integration does not appear in Add integration | Install a published release, keep the complete `custom_components/mbecocoach` directory and restart Home Assistant. HACS catalog review is still pending; use **Custom repositories** in the meantime. |
| Browser login cannot open `ecocoach://` | This desktop-browser error is expected for an app-specific redirect. Copy the complete fresh callback URL into the Home Assistant form within ten minutes; try another desktop browser if the first hides the URL. Never publish the callback. |
| Login succeeds but vehicle statistics fail | Use the Mercedes account entitled to Eco Coach for this VIN. A different account can pass Mercedes login yet fail the vehicle-specific API check. Confirm the VIN locally; do not include it in an issue. |
| Direct login asks for MFA or extra consent | The experimental direct flow cannot complete these screens. Use browser-assisted login instead. |
| Manual-token entry requires reauthentication | Manual access tokens cannot renew themselves. Reauthenticate with browser/direct login or supply a new token. Automatic renewal for OAuth entries is implemented but not yet confirmed at real live expiry. |
| A sensor is unknown | The provider may not have returned that metric yet; allow for a normal 15-minute update. Check integration availability and account/vehicle access. |
| Card is not offered or no vehicle is selected | Restart Home Assistant, reload the dashboard, ensure the integration is active, and select **Total account points** in the card editor. |
| Full-history re-import fails | Wait for Eco Coach connectivity to recover, then try once more. Existing cached awards are kept. Full history can take longer than statistics polling. |
| Old awards do not appear as new events | Expected: the event entity reports only new awards after startup, not historical activity. Browse old awards in the card or through the history action. |

## Safe logging

For a private diagnosis only, enable integration-specific logging in your
Home Assistant `configuration.yaml` and restart Home Assistant:

```yaml
logger:
  logs:
    custom_components.mbecocoach: debug
```

Messages from this logger use stage/endpoint names and HTTP status codes
without printing credentials or API response bodies. Other loggers,
especially HTTP wire logging and full Home Assistant logs, **may still
expose private information**. Inspect privately, remove the temporary
setting after troubleshooting, and do not upload raw logs. When opening a
[GitHub issue](https://github.com/aavdberg/ha-mbecocoach/issues), describe
the steps, Home Assistant version and a manually sanitized error summary
without usernames, passwords, tokens, callback URLs, VINs or trip data.
