"""Optional URL fetching via the standard library only (no network deps).

The core auditor is offline; this is a thin convenience so ``geo-audit check
https://...`` works. Tests never hit the network - they run against local
fixtures - which keeps the suite deterministic.
"""

from __future__ import annotations

import urllib.request

_USER_AGENT = "geo-auditor/0.1 (+https://github.com/baronguyen001/geo-auditor)"


def is_url(target: str) -> bool:
    return target.startswith(("http://", "https://"))


def fetch_url(url: str, *, timeout: float = 15.0) -> str:
    """Fetch *url* and return the decoded body.

    Raises ``ValueError`` for a non-HTTP(S) target and propagates urllib errors
    so the CLI can report them cleanly.
    """
    if not is_url(url):
        raise ValueError(f"Not an HTTP(S) URL: {url}")
    request = urllib.request.Request(  # noqa: S310 - scheme guarded by is_url above
        url, headers={"User-Agent": _USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        charset = response.headers.get_content_charset() or "utf-8"
        body: bytes = response.read()
    return body.decode(charset, errors="replace")
