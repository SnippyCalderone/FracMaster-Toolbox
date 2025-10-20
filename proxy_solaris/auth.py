import os
import threading
import time
from typing import Optional, Tuple

import httpx
from dotenv import load_dotenv

_THIS_DIR = os.path.dirname(__file__)
load_dotenv(dotenv_path=os.path.join(_THIS_DIR, ".env"))

BASE = os.getenv("SOLARIS_BASE_URL", "").rstrip("/")
USERNAME = os.getenv("SOLARIS_USERNAME", "")
PASSWORD = os.getenv("SOLARIS_PASSWORD", "")

# Docs: POST /api/v3/solaris/auth  (login)
LOGIN_PATH = "/solaris/auth"
# If your docs show a different refresh path, change this:
REFRESH_PATH = "/solaris/auth/refresh"

_lock = threading.Lock()
_access_token: Optional[str] = None
_refresh_token: Optional[str] = None
_expires_at: float = 0.0  # epoch seconds


def _raise_with_body(r: httpx.Response) -> None:
    try:
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        text = r.text
        raise RuntimeError(f"{r.status_code} {r.request.method} {r.request.url} :: {text}") from e


def _post_login_like(path: str, payload: dict) -> dict:
    """
    Try JSON first (as shown in some docs), then x-www-form-urlencoded,
    because some environments accept only one of them.
    """
    if not BASE:
        raise RuntimeError("SOLARIS_BASE_URL is not set")
    url = f"{BASE}{path if path.startswith('/') else '/' + path}"

    with httpx.Client(timeout=10) as c:
        # Attempt 1: JSON
        r = c.post(url, json=payload, headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        if r.status_code == 400:
            # Attempt 2: form-encoded (common alternative)
            r = c.post(url, data=payload, headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            })
        _raise_with_body(r)
        return r.json()


def _extract_tokens(payload: dict) -> Tuple[str, Optional[str], float]:
    """
    Extract tokens + expiry with flexible field names.
    """
    at = payload.get("access_token") or payload.get("accessToken") or payload.get("token")
    rt = payload.get("refresh_token") or payload.get("refreshToken")

    now = time.time()
    exp_abs = payload.get("expires_at") or payload.get("expiresAt") or payload.get("expiration")
    if isinstance(exp_abs, (int, float)):
        exp = float(exp_abs)
    else:
        exp_rel = payload.get("expires_in") or payload.get("expiresIn")
        exp = (now + float(exp_rel)) if isinstance(exp_rel, (int, float)) else (now + 55 * 60)

    if not at:
        raise RuntimeError(f"Login/refresh response missing access token fields: {payload}")

    return at, rt, exp


def login(force: bool = False) -> str:
    """Login with username/password; cache tokens in-memory."""
    global _access_token, _refresh_token, _expires_at
    if not USERNAME or not PASSWORD:
        raise RuntimeError("SOLARIS_USERNAME and SOLARIS_PASSWORD must be set")

    with _lock:
        if _access_token and not force and time.time() < _expires_at - 60:
            return _access_token

        payload = {"username": USERNAME, "password": PASSWORD}
        data = _post_login_like(LOGIN_PATH, payload)
        at, rt, exp = _extract_tokens(data)
        _access_token, _refresh_token, _expires_at = at, rt, exp
        return _access_token


def refresh() -> str:
    """Refresh using refresh token when available; otherwise re-login."""
    global _access_token, _refresh_token, _expires_at
    with _lock:
        if not _refresh_token:
            return login(force=True)

        data = _post_login_like(REFRESH_PATH, {"refresh_token": _refresh_token})
        at, rt, exp = _extract_tokens(data)
        _access_token, _refresh_token, _expires_at = at, (rt or _refresh_token), exp
        return _access_token


def get_access_token() -> str:
    """Return a valid token; login if none; refresh if near expiry."""
    with _lock:
        if _access_token and time.time() < _expires_at - 60:
            return _access_token
    try:
        return login()
    except Exception:
        return refresh()
