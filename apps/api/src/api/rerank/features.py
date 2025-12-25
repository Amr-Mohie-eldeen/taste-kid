from __future__ import annotations

from datetime import date
from typing import Iterable

from api.rerank.style_keywords import STYLE_KEYWORDS


def _split_items(value: str | None) -> set[str]:
    if not value:
        return set()
    parts = [item.strip().lower() for item in value.split(",")]
    return {item for item in parts if item}


def parse_genres(genres_str: str | None) -> set[str]:
    return _split_items(genres_str)


def parse_keywords(keywords_str: str | None) -> set[str]:
    return _split_items(keywords_str)


def extract_year(release_date: date | str | None) -> int | None:
    if release_date is None:
        return None
    if isinstance(release_date, date):
        return release_date.year
    value = str(release_date).strip()
    if len(value) >= 4 and value[:4].isdigit():
        return int(value[:4])
    return None


def style_keywords(keywords: Iterable[str]) -> set[str]:
    return {kw for kw in keywords if kw in STYLE_KEYWORDS}
