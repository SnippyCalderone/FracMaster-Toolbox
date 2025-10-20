import os
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv

from auth import get_access_token, refresh

_THIS_DIR = os.path.dirname(__file__)
load_dotenv(dotenv_path=os.path.join(_THIS_DIR, ".env"))

BASE = os.getenv("SOLARIS_BASE_URL", "").rstrip("/")
TIMEOUT = httpx.Timeout(10.0, connect=10.0)


def _headers(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    h: Dict[str, str] = {"Accept": "application/json"}
    token = get_access_token()
    h["Authorization"] = f"Bearer {token}"
    if extra:
        h.update(extra)
    return h


def _url(path: str) -> str:
    if not BASE:
        raise RuntimeError("SOLARIS_BASE_URL is not set")
    return f"{BASE}{path if path.startswith('/') else '/' + path}"


def get_json(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    url = _url(path)
    with httpx.Client(timeout=TIMEOUT) as c:
        r = c.get(url, headers=_headers(), params=params)
        if r.status_code == 401:
            refresh()
            r = c.get(url, headers=_headers(), params=params)

        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"{e.response.status_code} {url} :: {e.response.text}") from e
        return r.json()
