"""
Google Sign-In via the standard OAuth 2.0 authorization code flow.

Deliberately does not use an SDK - it's three plain HTTPS calls (build the
consent URL, exchange the code for a token, fetch the user's identity),
which keeps the dependency footprint small and the flow auditable.

All outbound calls have a short timeout and never propagate raw exceptions
up to the caller - a failure here must degrade to "try again", never to a
leaked stack trace or a hung request.
"""
import secrets
from urllib.parse import urlencode

import requests
from flask import current_app

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"
REQUEST_TIMEOUT_SECONDS = 6


class GoogleOAuthError(Exception):
    pass


def is_configured() -> bool:
    cfg = current_app.config
    return bool(cfg.get("GOOGLE_CLIENT_ID") and cfg.get("GOOGLE_CLIENT_SECRET") and cfg.get("GOOGLE_REDIRECT_URI"))


def generate_state() -> str:
    return secrets.token_urlsafe(24)


def build_consent_url(state: str) -> str:
    cfg = current_app.config
    params = {
        "client_id": cfg["GOOGLE_CLIENT_ID"],
        "redirect_uri": cfg["GOOGLE_REDIRECT_URI"],
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(params)}"


def exchange_code_for_identity(code: str) -> dict:
    """Exchanges an authorization code for tokens, then fetches the
    verified identity (email, name). Raises GoogleOAuthError on any
    failure - network error, bad response, or an unverified email."""
    cfg = current_app.config
    try:
        token_resp = requests.post(
            GOOGLE_TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": cfg["GOOGLE_CLIENT_ID"],
                "client_secret": cfg["GOOGLE_CLIENT_SECRET"],
                "redirect_uri": cfg["GOOGLE_REDIRECT_URI"],
                "grant_type": "authorization_code",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        token_resp.raise_for_status()
        access_token = token_resp.json().get("access_token")
        if not access_token:
            raise GoogleOAuthError("No access token returned")

        userinfo_resp = requests.get(
            GOOGLE_USERINFO_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        userinfo_resp.raise_for_status()
        info = userinfo_resp.json()
    except requests.RequestException as e:
        raise GoogleOAuthError(f"Google identity exchange failed: {e}") from e
    except ValueError as e:
        raise GoogleOAuthError("Invalid response from Google") from e

    if not info.get("email"):
        raise GoogleOAuthError("Google account has no email")
    if not info.get("email_verified"):
        raise GoogleOAuthError("Google email is not verified")

    return {
        "email": info["email"].strip().lower(),
        "name": info.get("name") or info["email"].split("@")[0],
        "google_id": info.get("sub"),
    }
