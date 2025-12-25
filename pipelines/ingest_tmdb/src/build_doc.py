from __future__ import annotations

import re
from datetime import date

def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def build_movie_doc(row: dict) -> str:
    title = (row.get("title") or "").strip()
    original_title = (row.get("original_title") or "").strip()
    release_date = row.get("release_date")

    year = ""
    if isinstance(release_date, date):
        year = str(release_date.year)

    genres = (row.get("genres") or "").strip()
    keywords = (row.get("keywords") or "").strip()
    tagline = (row.get("tagline") or "").strip()
    overview = (row.get("overview") or "").strip()

    parts = []
    if title:
        parts.append(f"{title}" + (f" ({year})" if year else ""))
    if original_title and original_title.lower() != title.lower():
        parts.append(f"Original title: {original_title}")
    if genres:
        parts.append(f"Genres: {genres}")
    if keywords:
        parts.append(f"Keywords: {keywords}")
    if tagline:
        parts.append(f"Tagline: {tagline}")
    if overview:
        parts.append(f"Overview: {overview}")

    return _clean(" | ".join(parts))