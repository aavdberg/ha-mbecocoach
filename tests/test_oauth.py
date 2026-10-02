"""Synthetic tests for Eco Coach PKCE and token rotation."""

from __future__ import annotations

import base64
import hashlib
import time
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import parse_qs, urlsplit

import pytest

from custom_components.mbecocoach.api import EcoCoachAuthError, EcoCoachError
from custom_components.mbecocoach.oauth import OAuthAttempt, exchange_code, refresh_tokens


def session_with_response(status: int, payload: object) -> MagicMock:
    """Construct a local HTTP stub; no real identity endpoint contacted."""
    response = MagicMock(status=status)
    response.json = AsyncMock(return_value=payload)
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=response)
    context.__aexit__ = AsyncMock(return_value=False)
    session = MagicMock()
    session.post.return_value = context
    return session


def test_authorization_url_and_callback_validation() -> None:
    """PKCE is SHA-256 based and only the matching redirect/state yields a code."""
    attempt = OAuthAttempt()
    query = parse_qs(urlsplit(attempt.url).query)
    assert query["client_id"] == ["022bed8c-3a28-4b1d-b465-9ca0f406b34e"]
    assert query["redirect_uri"] == ["ecocoach://login/callback"]
    assert query["scope"] == ["openid offline_access email phone profile ciam-uid"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"] == [
        base64.urlsafe_b64encode(hashlib.sha256(attempt.verifier.encode()).digest()).rstrip(b"=").decode()
    ]
    assert attempt.verifier not in attempt.url
    assert attempt.extract_code(f"ecocoach://login/callback?code=synthetic&state={attempt.state}") == "synthetic"
    with pytest.raises(EcoCoachAuthError):
        attempt.extract_code(f"ecocoach://login/callback?code=synthetic&state={attempt.state}")


@pytest.mark.parametrize(
    "callback",
    [
        "https://evil.example/callback?code=a&state=STATE",
        "ecocoach://login/callback?code=a&state=other",
        "ecocoach://login/callback?code=a&code=b&state=STATE",
        "ecocoach://login/callback?code=&state=STATE",
    ],
)
def test_callback_rejected(callback: str) -> None:
    """Reject external URLs, mismatched state and missing/duplicate codes."""
    attempt = OAuthAttempt()
    with pytest.raises(EcoCoachAuthError):
        attempt.extract_code(callback.replace("STATE", attempt.state))


def test_expired_attempt() -> None:
    """Do not exchange a code after the short-lived PKCE state expires."""
    attempt = OAuthAttempt()
    attempt.created = time.monotonic() - 601
    with pytest.raises(EcoCoachAuthError):
        attempt.extract_code(f"ecocoach://login/callback?code=a&state={attempt.state}")


@pytest.mark.asyncio
async def test_code_exchange_and_refresh() -> None:
    """Exchange a one-time code, then rotate both tokens with the captured grant."""
    session = session_with_response(200, {"access_token": "access", "refresh_token": "refresh", "expires_in": 3600})
    attempt = OAuthAttempt()
    tokens = await exchange_code(session, attempt, f"ecocoach://login/callback?code=one-time&state={attempt.state}")
    assert tokens.access_token == "access"
    assert tokens.refresh_token == "refresh"
    assert tokens.expires_at > time.time()
    data = session.post.call_args.kwargs["data"]
    assert data["code_verifier"] == attempt.verifier
    assert data["redirect_uri"] == "ecocoach://login/callback"
    await refresh_tokens(session, tokens.refresh_token)
    assert session.post.call_args.kwargs["data"] == {"grant_type": "refresh_token", "refresh_token": "refresh"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "payload", "error"),
    [
        (401, None, EcoCoachAuthError),
        (500, None, EcoCoachError),
        (200, {"access_token": "a", "expires_in": 3600}, EcoCoachError),
        (200, {"access_token": "a", "refresh_token": "b", "expires_in": True}, EcoCoachError),
    ],
)
async def test_token_failures(status: int, payload: object, error: type[Exception]) -> None:
    """Never accept a success-shaped partial token or silently swallow errors."""
    with pytest.raises(error):
        await refresh_tokens(session_with_response(status, payload), "synthetic")
