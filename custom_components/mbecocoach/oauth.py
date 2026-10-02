"""Eco Coach's observed authorization-code + PKCE flow."""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urlsplit

from aiohttp import ClientError, ClientSession

from .api import EcoCoachAuthError, EcoCoachConnectionError, EcoCoachError

CLIENT_ID = "022bed8c-3a28-4b1d-b465-9ca0f406b34e"
REDIRECT_URI = "ecocoach://login/callback"
SCOPE = "openid offline_access email phone profile ciam-uid"
AUTH_URL = "https://id.mercedes-benz.com/as/authorization.oauth2"
TOKEN_URL = "https://id.mercedes-benz.com/as/token.oauth2"


@dataclass(frozen=True)
class TokenSet:
    """Persistable token data returned by Mercedes Identity."""

    access_token: str
    refresh_token: str
    expires_at: float


class OAuthAttempt:
    """One short-lived, state-bound PKCE authorization attempt."""

    def __init__(self) -> None:
        """Generate secrets for this flow; never store them in a config entry."""
        self.verifier = secrets.token_urlsafe(64)
        self.state = secrets.token_urlsafe(32)
        self.created = time.monotonic()
        self._used = False

    @property
    def url(self) -> str:
        """Return the browser URL without exposing the code verifier."""
        challenge = base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest()).rstrip(b"=").decode()
        return (
            AUTH_URL
            + "?"
            + urlencode(
                {
                    "client_id": CLIENT_ID,
                    "redirect_uri": REDIRECT_URI,
                    "scope": SCOPE,
                    "response_type": "code",
                    "code_challenge_method": "S256",
                    "code_challenge": challenge,
                    "state": self.state,
                }
            )
        )

    def extract_code(self, callback: str) -> str:
        """Require the complete, matching redirect before exchanging its code."""
        if self._used or time.monotonic() - self.created > 600:
            raise EcoCoachAuthError("Authorization attempt expired; start again")
        if len(callback) > 4096:
            raise EcoCoachAuthError("Authorization redirect is too long")
        try:
            url = urlsplit(callback.strip())
        except ValueError as err:
            raise EcoCoachAuthError("Unexpected authorization redirect") from err
        if (url.scheme, url.netloc, url.path) != ("ecocoach", "login", "/callback") or url.fragment:
            raise EcoCoachAuthError("Unexpected authorization redirect")
        params = parse_qs(url.query, keep_blank_values=True)
        if params.get("state") != [self.state] or len(params.get("code", [])) != 1 or not params["code"][0]:
            raise EcoCoachAuthError("Authorization state or code is invalid")
        self._used = True
        return params["code"][0]


async def request_tokens(session: ClientSession, data: dict[str, str]) -> TokenSet:
    """Exchange a code or refresh token, without logging any HTTP bodies."""
    try:
        async with session.post(TOKEN_URL, data=data, timeout=15) as response:
            if response.status in (400, 401, 403):
                raise EcoCoachAuthError("Mercedes rejected the authorization or refresh token")
            if response.status != 200:
                raise EcoCoachError(f"Mercedes token service returned HTTP {response.status}")
            try:
                payload = await response.json()
            except (ValueError, ClientError) as err:
                raise EcoCoachError("Mercedes token response is not valid JSON") from err
    except (TimeoutError, ClientError) as err:
        raise EcoCoachConnectionError("Mercedes token service is unreachable") from err
    if not isinstance(payload, dict):
        raise EcoCoachError("Mercedes token response is invalid")
    access = payload.get("access_token")
    refresh = payload.get("refresh_token")
    expiry = payload.get("expires_in")
    if (
        not isinstance(access, str)
        or not access
        or not isinstance(refresh, str)
        or not refresh
        or isinstance(expiry, bool)
        or not isinstance(expiry, (int, float))
        or not 0 < expiry <= 86400
    ):
        raise EcoCoachError("Mercedes token response is missing required fields")
    return TokenSet(access, refresh, time.time() + expiry)


async def exchange_code(session: ClientSession, attempt: OAuthAttempt, callback: str) -> TokenSet:
    """Exchange a one-time code with the verifier kept inside HA."""
    return await request_tokens(
        session,
        {
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "code": attempt.extract_code(callback),
            "code_verifier": attempt.verifier,
        },
    )


async def refresh_tokens(session: ClientSession, refresh: str) -> TokenSet:
    """Rotate access and refresh tokens using the captured refresh grant."""
    return await request_tokens(session, {"grant_type": "refresh_token", "refresh_token": refresh})
