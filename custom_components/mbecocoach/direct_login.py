"""Optional Mercedes CIAM login without a desktop custom-URI handler."""

from __future__ import annotations

import logging
import uuid
from urllib.parse import parse_qs, urljoin, urlsplit

from aiohttp import ClientError, ClientSession, CookieJar
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from yarl import URL

from .api import EcoCoachAuthError, EcoCoachConnectionError, EcoCoachError
from .oauth import AUTH_URL, OAuthAttempt, TokenSet, exchange_code

_ORIGIN = "https://id.mercedes-benz.com"
_LOGGER = logging.getLogger(__name__)
_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Origin": _ORIGIN,
    "Referer": f"{_ORIGIN}/ciam/auth/login",
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 15_8_3 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6.6 Mobile/15E148 Safari/604.1"
    ),
}


class EcoCoachMfaRequired(EcoCoachAuthError):
    """Mercedes requires an additional interactive authentication step."""


class EcoCoachUnsupportedLogin(EcoCoachError):
    """Mercedes returned an additional or changed sign-in step."""


def _resume_path(final_url: str) -> str:
    """Return the same-origin authorization continuation from CIAM."""
    url = urlsplit(final_url)
    if (url.scheme, url.netloc, url.path) != ("https", "id.mercedes-benz.com", "/ciam/auth/login"):
        raise EcoCoachAuthError("Mercedes did not return the expected login page")
    resume = parse_qs(url.query).get("resume", [])
    if len(resume) != 1 or not resume[0].startswith("/") or resume[0].startswith("//"):
        raise EcoCoachAuthError("Mercedes did not provide an authorization continuation")
    target = urlsplit(urljoin(_ORIGIN, resume[0]))
    if (target.scheme, target.netloc, target.path) != (
        "https",
        "id.mercedes-benz.com",
        "/as/authorization.oauth2",
    ) or target.fragment:
        raise EcoCoachAuthError("Invalid Mercedes authorization continuation")
    return resume[0]


async def _post_json(session: ClientSession, path: str, payload: dict[str, str | bool]) -> dict:
    """Post CIAM data without exposing response bodies or credentials in errors."""
    async with session.post(
        f"{_ORIGIN}{path}", json=payload, headers=_HEADERS, allow_redirects=False, timeout=15
    ) as response:
        if response.status in (400, 401, 403):
            _LOGGER.warning("Eco Coach direct login password step rejected (HTTP %d)", response.status)
            raise EcoCoachAuthError("Mercedes rejected this login step")
        if response.status != 200:
            _LOGGER.warning("Eco Coach direct login password step failed (HTTP %d)", response.status)
            raise EcoCoachError(f"Mercedes login returned HTTP {response.status}")
        try:
            data = await response.json()
        except (ValueError, ClientError) as err:
            raise EcoCoachError("Mercedes login response is not valid JSON") from err
    if not isinstance(data, dict):
        raise EcoCoachError("Mercedes login response is invalid")
    return data


async def _login(session: ClientSession, username: str, password: str) -> TokenSet:
    attempt = OAuthAttempt()
    async with session.get(attempt.url, headers=_HEADERS, timeout=15) as response:
        if response.status != 200:
            _LOGGER.warning("Eco Coach direct login authorization failed (HTTP %d)", response.status)
            raise EcoCoachError(f"Mercedes authorization returned HTTP {response.status}")
        try:
            resume = _resume_path(str(response.url))
        except EcoCoachAuthError:
            _LOGGER.warning("Eco Coach direct login authorization continuation is invalid")
            raise

    async with session.post(
        f"{_ORIGIN}/ciam/auth/ua",
        json={"browserName": "Mobile Safari", "browserVersion": "15.6.6", "osName": "iOS"},
        headers=_HEADERS,
        allow_redirects=False,
        timeout=15,
    ) as response:
        if not 200 <= response.status < 300:
            _LOGGER.warning("Eco Coach direct login browser setup failed (HTTP %d)", response.status)
            raise EcoCoachError(f"Mercedes browser setup returned HTTP {response.status}")
    async with session.post(
        f"{_ORIGIN}/ciam/auth/login/user",
        json={"username": username},
        headers=_HEADERS,
        allow_redirects=False,
        timeout=15,
    ) as response:
        if response.status in (400, 401, 403):
            _LOGGER.warning("Eco Coach direct login username step rejected (HTTP %d)", response.status)
            raise EcoCoachAuthError("Mercedes rejected the username")
        if not 200 <= response.status < 300:
            _LOGGER.warning("Eco Coach direct login username step failed (HTTP %d)", response.status)
            raise EcoCoachError(f"Mercedes username step returned HTTP {response.status}")
    outcome = await _post_json(
        session,
        "/ciam/auth/login/pass",
        {"username": username, "password": password, "rememberMe": False, "rid": uuid.uuid4().hex},
    )
    if outcome.get("result") == "GOTO_LOGIN_OTP":
        _LOGGER.warning("Eco Coach direct login requires MFA")
        raise EcoCoachMfaRequired("Mercedes requires MFA; use browser login")
    if outcome.get("result") != "RESUME2OIDCP" or not isinstance(outcome.get("token"), str) or not outcome["token"]:
        _LOGGER.warning("Eco Coach direct login returned an unsupported password-step result")
        raise EcoCoachUnsupportedLogin("Mercedes login requires an unsupported additional step")

    async with session.post(
        f"{_ORIGIN}{resume}",
        data={"token": outcome["token"]},
        headers={**_HEADERS, "Accept": "text/html,application/xhtml+xml"},
        allow_redirects=False,
        timeout=15,
    ) as response:
        if response.status not in (301, 302, 303):
            _LOGGER.warning("Eco Coach direct login authorization resume failed (HTTP %d)", response.status)
            raise EcoCoachAuthError("Mercedes did not finish the authorization")
        callback = response.headers.get("Location", "")
    try:
        return await exchange_code(session, attempt, callback)
    except EcoCoachError:
        _LOGGER.warning("Eco Coach direct login code exchange failed")
        raise


async def async_direct_login(hass: HomeAssistant, username: str, password: str) -> TokenSet:
    """Run a one-shot login in an isolated cookie session; never persist the password."""
    jar = CookieJar()
    jar.update_cookies({"CIAM.DEVICE": str(uuid.uuid4())}, response_url=URL(AUTH_URL))
    session = async_create_clientsession(hass, auto_cleanup=False, cookie_jar=jar)
    try:
        try:
            return await _login(session, username, password)
        except (TimeoutError, ClientError) as err:
            raise EcoCoachConnectionError("Mercedes login is unreachable") from err
    finally:
        session.detach()
