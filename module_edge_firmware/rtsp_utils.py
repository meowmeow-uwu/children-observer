"""Utilities shared by Edge RTSP readers."""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit


def redact_rtsp_url(url: str) -> str:
    """Return an RTSP URL safe to write to logs.

    Camera credentials commonly live in the authority portion of an RTSP URL.
    Keep the endpoint visible for troubleshooting while never exposing that
    credential in terminal output or journald.
    """

    try:
        parts = urlsplit(url)
    except ValueError:
        # A malformed URL is still not safe to emit verbatim.  This fallback
        # covers the usual ``user:password@host`` form without parsing it.
        return "<credentials-redacted>" if "@" in url else url

    if "@" not in parts.netloc:
        return url

    endpoint = parts.netloc.rsplit("@", 1)[1]
    return urlunsplit(
        (parts.scheme, f"<credentials-redacted>@{endpoint}", parts.path, parts.query, parts.fragment)
    )
