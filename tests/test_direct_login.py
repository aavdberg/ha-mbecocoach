"""Synthetic tests for the optional isolated Mercedes login session."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.mbecocoach.api import EcoCoachAuthError
from custom_components.mbecocoach.direct_login import (
    EcoCoachMfaRequired,
    EcoCoachUnsupportedLogin,
    _login,
    _resume_path,
    async_direct_login,
)
from custom_components.mbecocoach.oauth import TokenSet


def reply(status: int, *, url: str = "", location: str = "", payload: dict | None = None) -> MagicMock:
    """Mock an aiohttp response context without contacting Mercedes."""
    response = MagicMock(status=status, url=url, headers={"Location": location})
    response.json = AsyncMock(return_value=payload)
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=response)
    context.__aexit__ = AsyncMock(return_value=False)
    return context


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.invalid/ciam/auth/login?resume=/as/resume",
        "https://id.mercedes-benz.com/ciam/auth/login?resume=https://evil.invalid/",
        "https://id.mercedes-benz.com/ciam/auth/login?resume=//evil.invalid/",
        "https://id.mercedes-benz.com/ciam/auth/login?resume=/ciam/auth/login/pass",
        "https://id.mercedes-benz.com/ciam/auth/login?resume=/as/authorization.oauth2%23fragment",
        "https://id.mercedes-benz.com/ciam/auth/login",
    ],
)
def test_only_same_origin_resume(url: str) -> None:
    """Never post a CIAM login token to a foreign host or unspecified path."""
    with pytest.raises(EcoCoachAuthError):
        _resume_path(url)


@pytest.mark.asyncio
async def test_direct_login_exchanges_state_bound_redirect() -> None:
    """Complete the server-side handshake without putting credentials in tokens."""
    session = MagicMock()
    session.get.return_value = reply(
        200, url="https://id.mercedes-benz.com/ciam/auth/login?resume=/as/authorization.oauth2%3Fresume%3Dabc"
    )
    session.post.side_effect = [
        reply(200),
        reply(200, payload={}),
        reply(200, payload={"result": "RESUME2OIDCP", "token": "pre-login"}),
        reply(302, location="ecocoach://login/callback?code=synthetic&state=state"),
    ]
    with (
        patch("custom_components.mbecocoach.direct_login.OAuthAttempt") as attempt,
        patch("custom_components.mbecocoach.direct_login.exchange_code", new_callable=AsyncMock) as exchange,
    ):
        attempt.return_value.url = "https://id.mercedes-benz.com/as/authorization.oauth2?synthetic"
        exchange.return_value = TokenSet("access", "refresh", 123)
        result = await _login(session, "example", "password")
    assert result.access_token == "access"
    assert exchange.await_args.args[2] == "ecocoach://login/callback?code=synthetic&state=state"
    assert session.post.call_args_list[2].args[0].endswith("/ciam/auth/login/pass")
    assert all(call.kwargs["allow_redirects"] is False for call in session.post.call_args_list)


@pytest.mark.asyncio
async def test_mfa_stops_before_code_exchange() -> None:
    """Do not guess or silently bypass an interactive login challenge."""
    session = MagicMock()
    session.get.return_value = reply(
        200, url="https://id.mercedes-benz.com/ciam/auth/login?resume=/as/authorization.oauth2"
    )
    session.post.side_effect = [
        reply(200),
        reply(200, payload={}),
        reply(200, payload={"result": "GOTO_LOGIN_OTP"}),
    ]
    with (
        patch("custom_components.mbecocoach.direct_login.OAuthAttempt"),
        patch("custom_components.mbecocoach.direct_login.exchange_code", new_callable=AsyncMock) as exchange,
    ):
        with pytest.raises(EcoCoachMfaRequired):
            await _login(session, "example", "password")
        exchange.assert_not_awaited()


@pytest.mark.asyncio
async def test_unsupported_login_step_stops_before_code_exchange() -> None:
    """Distinguish changed account verification from invalid credentials."""
    session = MagicMock()
    session.get.return_value = reply(
        200, url="https://id.mercedes-benz.com/ciam/auth/login?resume=/as/authorization.oauth2"
    )
    session.post.side_effect = [reply(200), reply(200), reply(200, payload={"result": "GOTO_CONSENT"})]
    with patch("custom_components.mbecocoach.direct_login.exchange_code", new_callable=AsyncMock) as exchange:
        with pytest.raises(EcoCoachUnsupportedLogin):
            await _login(session, "example", "password")
        exchange.assert_not_awaited()


@pytest.mark.asyncio
async def test_isolated_cookie_session_always_closes() -> None:
    """Do not leak password-era session cookies into the HA API session."""
    session = MagicMock()
    session.close = AsyncMock()
    with (
        patch("custom_components.mbecocoach.direct_login.async_create_clientsession", return_value=session) as create,
        patch("custom_components.mbecocoach.direct_login._login", new_callable=AsyncMock) as login,
    ):
        login.side_effect = EcoCoachAuthError("Rejected")
        with pytest.raises(EcoCoachAuthError):
            await async_direct_login(MagicMock(), "example", "password")
    assert create.call_args.kwargs["auto_cleanup"] is False
    login.assert_awaited_once()
    session.close.assert_awaited_once()
