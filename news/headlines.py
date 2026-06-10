# -*- coding: utf-8 -*-
"""Free news headlines via yfinance (Yahoo Finance). No paid APIs."""
try:
    import yfinance as yf
except ImportError:
    yf = None


def get_headlines(symbol: str, limit: int = 5) -> list[dict]:
    """Return up to `limit` recent headlines for `symbol`.

    Each item is {title, publisher, link}. Best-effort: returns [] on any
    failure, since news is a nice-to-have and the schema varies over time.
    """
    if yf is None:
        return []
    try:
        items = yf.Ticker(symbol).news or []
    except Exception:
        return []

    out: list[dict] = []
    for it in items[:limit]:
        # yfinance has shipped two news schemas; dig defensively for both.
        content = it.get("content", it)
        title = content.get("title") or it.get("title")
        if not title:
            continue
        publisher = (
            (content.get("provider") or {}).get("displayName")
            or it.get("publisher")
            or ""
        )
        link = (
            (content.get("canonicalUrl") or {}).get("url")
            or it.get("link")
            or ""
        )
        out.append({"title": title, "publisher": publisher, "link": link})
    return out
