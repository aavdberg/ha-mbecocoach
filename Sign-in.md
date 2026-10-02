# Sign in to Eco Coach

[Home](Home) · [Installation](Installation) · [Troubleshooting](Troubleshooting)

In **Settings → Devices & services → Add integration → Mercedes Eco Coach**,
enter the vehicle's 17-character VIN. Sign in with the Mercedes account that
is actually entitled to use Eco Coach for that vehicle; another Mercedes
account can complete login yet fail the vehicle statistics check.

There are three ways to provide access:

| Method | When to use it | Important limitation |
| --- | --- | --- |
| Browser-assisted login (default) | Preferred method; no password entered into Home Assistant | Requires a desktop browser and manually pasting a one-time callback URL |
| Direct login (experimental) | If the account's sign-in screen follows the supported basic flow | Password is entered once in Home Assistant; MFA and extra consent screens are not supported |
| Existing access token | If you already have an Eco Coach bearer token | Manual-token entries cannot renew tokens automatically |

## Browser-assisted login

1. Enter the VIN, leave the **optional access token blank**, and keep the
   default **browser** login mode.
2. On the next form, copy the **prefilled authorization URL above the
   `callback_url` field** into a **desktop browser without the Eco Coach
   mobile app installed**. Home Assistant does not launch the browser.
3. Sign in to Mercedes Identity. Because this integration uses the mobile
   app's registered `ecocoach://login/callback` redirect, a desktop browser
   may report that it cannot open the link. That is expected.
4. Copy the **complete fresh** `ecocoach://login/callback...` URL, including
   its query parameters, from the address bar or browser history, and paste
   it **only** into your local Home Assistant `callback_url` field.
5. Submit within **ten minutes**. Home Assistant checks that the callback
   belongs to this login attempt, exchanges its one-time code, verifies
   vehicle statistics and stores OAuth tokens.

Do **not** use the iPhone Eco Coach app for this handoff: it may open the
callback itself instead of letting you copy it. Some browsers hide a
custom-scheme URL; in a tested Edge session it appeared only in the
browser's developer console. If you cannot obtain it, try a different
desktop browser or use the direct method if appropriate. **Never send the
callback URL to an issue, chat or anyone else**: it contains a short-lived
authorization code.

## Experimental direct login

1. Enter the VIN, leave the optional access token blank and select
   **direct** as the login mode.
2. In the next Home Assistant form, enter the Mercedes account username
   (email/phone) and password. Only do this on your own trusted Home
   Assistant instance.
3. The integration uses an isolated, temporary login session, verifies
   access to the vehicle's statistics and discards the password and session.
   It stores OAuth access/refresh tokens after a successful login.

This method succeeded with an account entitled to Eco Coach in a private
test, but it cannot complete MFA, unusual verification prompts or additional
consent screens. If Home Assistant reports an unsupported screen or MFA,
use the browser-assisted method. If it reports a **statistics verification**
failure, check that this account is entitled to Eco Coach for this VIN;
repeatedly submitting the same password will not fix a vehicle entitlement
problem.

## Existing access token and reauthentication

If you already have a valid Eco Coach bearer access token, enter it in the
optional field when adding the integration. Home Assistant verifies the
vehicle statistics before saving it. This legacy method does **not**
provide a refresh token; a replacement may be required when it expires.
Never paste an access token into an issue or public message.

Entries created through browser or direct login store access and refresh
tokens in Home Assistant's config entry storage and try to renew them before
expiry. Renewal at a **real live expiry** has not yet been verified. If
reauthentication appears, leave the token blank to choose browser/direct
login again, or enter a replacement access token. Secure Home Assistant's
storage and backups.
