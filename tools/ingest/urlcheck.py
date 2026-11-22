"""URL checks with a generic client name; nothing about the project or owner is sent."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, Dict, Optional

USER_AGENT = "link-checker/1.0"
ARCHIVE_API = "https://archive.org/wait/available?url="

Opener = Callable[[urllib.request.Request, float], object]


def default_opener(request: urllib.request.Request, timeout: float):
    return urllib.request.urlopen(request, timeout=timeout)  # noqa: S310 (http/https only, checked)


def _fetch(url: str, opener: Opener, method: str, timeout: float):
    req = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
    return opener(req, timeout)


def _status_of(url: str, opener: Opener, timeout: float) -> str:
    for method in ("HEAD", "GET"):
        try:
            resp = _fetch(url, opener, method, timeout)
            code = getattr(resp, "status", None) or resp.getcode()
            if hasattr(resp, "close"):
                resp.close()
            return "ok" if 200 <= int(code) < 400 else f"http_{code}"
        except urllib.error.HTTPError as exc:
            if method == "HEAD" and exc.code in (403, 405, 501):
                continue
            return f"http_{exc.code}"
        except Exception as exc:  # network, DNS, timeout, bad URL
            return f"error_{type(exc).__name__}"
    return "error"


def archive_lookup(url: str, opener: Opener, timeout: float = 15.0) -> Optional[str]:
    try:
        resp = _fetch(ARCHIVE_API + urllib.parse.quote(url, safe=""), opener, "GET", timeout)
        data = json.loads(resp.read().decode("utf-8"))
        snap = (data.get("archived_snapshots") or {}).get("closest") or {}
        return snap.get("url") if snap.get("available") else None
    except Exception:
        return None


def check_url(url: str, opener: Optional[Opener] = None, timeout: float = 15.0) -> Dict[str, Optional[str]]:
    """Return {"url_status": ..., "archive_url": ...}. Only http(s) URLs are fetched."""
    opener = opener or default_opener
    if urllib.parse.urlparse(url).scheme not in ("http", "https"):
        return {"url_status": "invalid", "archive_url": None}
    status = _status_of(url, opener, timeout)
    archive = None if status == "ok" else archive_lookup(url, opener, timeout)
    return {"url_status": status, "archive_url": archive}
