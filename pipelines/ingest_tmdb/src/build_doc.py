from __future__ import annotations

import re
from datetime import date
from typing import Iterable


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def _split_tokens(text: str) -> list[str]:
    """Split TMDB CSV fields that are typically comma-separated (sometimes pipes)."""
    t = _clean(text)
    if not t:
        return []
    parts = re.split(r"\s*,\s*|\s*\|\s*", t)
    out: list[str] = []
    seen: set[str] = set()
    for p in parts:
        p = _clean(p)
        k = p.lower()
        if not p or k in seen:
            continue
        seen.add(k)
        out.append(p)
    return out


def _top(items: Iterable[str], n: int) -> list[str]:
    out: list[str] = []
    for x in items:
        if not x:
            continue
        out.append(x)
        if len(out) >= n:
            break
    return out


def build_movie_doc(row: dict) -> str:
    """
    Build a text document optimized for semantic similarity.

    Opinionated defaults:
    - Overview/tagline carry most of the semantic signal.
    - Genres/keywords add context but easily become noisy, so we keep them short.
    """

    title = _clean(row.get("title"))
    original_title = _clean(row.get("original_title"))

    release_date = row.get("release_date")
    year = ""
    if isinstance(release_date, date):
        year = str(release_date.year)

    tagline = _clean(row.get("tagline"))
    overview = _clean(row.get("overview"))

    genres = _top(_split_tokens(row.get("genres") or ""), 5)
    keywords = _top(_split_tokens(row.get("keywords") or ""), 12)

    parts: list[str] = []

    if title:
        parts.append(f"{title}{f' ({year})' if year else ''}.")

    if original_title and original_title.lower() != title.lower():
        parts.append(f"Also known as {original_title}.")

    if tagline:
        parts.append(tagline + ("." if not tagline.endswith(".") else ""))

    if overview:
        parts.append(overview + ("." if not overview.endswith(".") else ""))

    if genres:
        parts.append("Genres: " + ", ".join(genres) + ".")

    if keywords:
        parts.append("Keywords: " + ", ".join(keywords) + ".")

    return _clean(" ".join(parts))