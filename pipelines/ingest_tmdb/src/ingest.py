from __future__ import annotations

import os
from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Iterable
from datetime import date

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert as pg_insert


@dataclass(frozen=True)
class Settings:
    csv_path: Path
    database_url: str
    chunksize: int = 200_000
    target_rows: int = 50_000


logger = logging.getLogger(__name__)


def _repo_root() -> Path:
    # pipelines/ingest_tmdb/src/ingest.py -> repo root is 3 parents up
    return Path(__file__).resolve().parents[3]


def _load_settings() -> Settings:
    root = _repo_root()
    # load root .env if present
    load_dotenv(root / ".env")

    csv_default = root / "data" / "raw" / "TMDB_movie_dataset_v11.csv"
    csv_path = Path(os.getenv("TMDB_CSV_PATH", str(csv_default))).expanduser().resolve()

    # When running locally with uv, Postgres is usually published on localhost:5432
    database_url = os.getenv(
        "DATABASE_URL",
        os.getenv(
            "DATABASE_URL_LOCAL",
            "postgresql+psycopg://app:app@localhost:5432/tmdb",
        ),
    )

    chunksize = int(os.getenv("TMDB_CHUNKSIZE", "200000"))
    target_rows = int(os.getenv("TMDB_TARGET_ROWS", "50000"))

    return Settings(
        csv_path=csv_path,
        database_url=database_url,
        chunksize=chunksize,
        target_rows=target_rows,
    )

def _setup_logging() -> None:
    if logging.getLogger().handlers:
        return

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)

def _dedupe_records(records: list[dict]) -> list[dict]:
    # keep the last occurrence per id
    by_id = {}
    for r in records:
        mid = r.get("id")
        if mid is not None:
            by_id[mid] = r
    return list(by_id.values())

def _normalize_bool(v) -> bool | None:
    if pd.isna(v):
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in {"true", "t", "1", "yes", "y"}:
        return True
    if s in {"false", "f", "0", "no", "n"}:
        return False
    return None


def _safe_int(v) -> int | None:
    if pd.isna(v):
        return None
    try:
        return int(float(v))
    except Exception:
        return None


def _safe_float(v) -> float | None:
    if pd.isna(v):
        return None
    try:
        return float(v)
    except Exception:
        return None


def _coerce_release_date(series: pd.Series) -> pd.Series:
    # Keep as datetime64[ns] for sorting; store in DB as date later (SQLAlchemy handles it)
    return pd.to_datetime(series, errors="coerce", utc=False)


def _select_top_rated_ids(csv_path: Path, chunksize: int, target_rows: int) -> tuple[set[int], int]:
    """
    First pass: read id + vote_average + vote_count + original_language,
    filter to English, and keep the top target_rows by vote_average, then vote_count.
    """
    keep = pd.DataFrame(columns=["id", "vote_average", "vote_count"])
    total_eligible = 0

    usecols = ["id", "vote_average", "vote_count", "original_language"]

    for chunk in pd.read_csv(csv_path, usecols=usecols, chunksize=chunksize):
        # Coerce id
        chunk["id"] = pd.to_numeric(chunk["id"], errors="coerce").astype("Int64")
        chunk = chunk.dropna(subset=["id"])
        chunk["id"] = chunk["id"].astype("int64")

        # Only English movies
        if "original_language" in chunk.columns:
            chunk = chunk[chunk["original_language"] == "en"]

        # Coerce votes
        chunk["vote_average"] = pd.to_numeric(chunk["vote_average"], errors="coerce")
        chunk["vote_count"] = pd.to_numeric(chunk["vote_count"], errors="coerce")
        chunk = chunk.dropna(subset=["vote_average", "vote_count"])
        chunk = chunk[chunk["vote_count"] >= 500]
        total_eligible += len(chunk)

        # Keep top N so far
        chunk = chunk.sort_values(["vote_average", "vote_count"], ascending=[False, False])
        keep = pd.concat([keep, chunk[["id", "vote_average", "vote_count"]]], ignore_index=True)
        keep = keep.sort_values(["vote_average", "vote_count"], ascending=[False, False]).head(target_rows)

    return set(keep["id"].astype("int64").tolist()), total_eligible


def _iter_recent_rows(csv_path: Path, ids: set[int], chunksize: int) -> Iterable[pd.DataFrame]:
    """
    Second pass: stream full rows but only emit rows whose id is in ids.
    """
    for chunk in pd.read_csv(csv_path, chunksize=chunksize):
        if "id" not in chunk.columns:
            raise ValueError("CSV missing required column: id")

        chunk["id"] = pd.to_numeric(chunk["id"], errors="coerce").astype("Int64")
        chunk = chunk.dropna(subset=["id"])
        chunk["id"] = chunk["id"].astype("int64")

        if "original_language" in chunk.columns:
            chunk = chunk[chunk["original_language"] == "en"]

        filtered = chunk[chunk["id"].isin(ids)]
        if not filtered.empty:
            yield filtered


def _prepare_records(df: pd.DataFrame) -> list[dict]:
    """
    Map dataframe columns to the movies table schema, with safe conversions.
    Drops any rows with release_date beyond today (garbage) or missing release_date.
    """

    if df.empty:
        return []

    def col(name: str) -> pd.Series:
        return df[name] if name in df.columns else pd.Series([None] * len(df), index=df.index)

    def normalize_str(name: str) -> pd.Series:
        s = col(name).astype("string")
        s = s.where(s.notna(), None)
        return s.astype(object)

    def normalize_int(name: str) -> pd.Series:
        s = pd.to_numeric(col(name), errors="coerce").astype("Int64")
        s = s.where(s.notna(), None)
        return s.astype(object)

    def normalize_float(name: str) -> pd.Series:
        s = pd.to_numeric(col(name), errors="coerce")
        s = s.where(s.notna(), None)
        return s.astype(object)

    def normalize_bool(name: str) -> pd.Series:
        return col(name).map(_normalize_bool)

    today = pd.Timestamp(date.today())

    # Parse release_date
    release_dt = _coerce_release_date(col("release_date"))
    # Clamp future dates to NaT
    release_dt = release_dt.where(release_dt <= today, pd.NaT)

    # Drop rows without a valid release date (after clamping)
    df2 = df.copy()
    df2["_release_dt"] = release_dt
    df2 = df2.dropna(subset=["_release_dt"])

    # Only English movies
    if "original_language" in df2.columns:
        df2 = df2[df2["original_language"] == "en"]

    # Re-align series after filtering
    release_dt = df2["_release_dt"]
    if df2.empty:
        return []

    records_df = pd.DataFrame(
        {
            "id": normalize_int("id").reindex(df2.index),
            "title": normalize_str("title").reindex(df2.index),
            "vote_average": normalize_float("vote_average").reindex(df2.index),
            "vote_count": normalize_int("vote_count").reindex(df2.index),
            "status": normalize_str("status").reindex(df2.index),
            "release_date": release_dt.dt.date,
            "revenue": normalize_int("revenue").reindex(df2.index),
            "runtime": normalize_int("runtime").reindex(df2.index),
            "adult": normalize_bool("adult").reindex(df2.index),
            "backdrop_path": normalize_str("backdrop_path").reindex(df2.index),
            "budget": normalize_int("budget").reindex(df2.index),
            "homepage": normalize_str("homepage").reindex(df2.index),
            "imdb_id": normalize_str("imdb_id").reindex(df2.index),
            "original_language": normalize_str("original_language").reindex(df2.index),
            "original_title": normalize_str("original_title").reindex(df2.index),
            "overview": normalize_str("overview").reindex(df2.index),
            "popularity": normalize_float("popularity").reindex(df2.index),
            "poster_path": normalize_str("poster_path").reindex(df2.index),
            "tagline": normalize_str("tagline").reindex(df2.index),
            "genres": normalize_str("genres").reindex(df2.index),
            "production_companies": normalize_str("production_companies").reindex(df2.index),
            "production_countries": normalize_str("production_countries").reindex(df2.index),
            "spoken_languages": normalize_str("spoken_languages").reindex(df2.index),
            "keywords": normalize_str("keywords").reindex(df2.index),
        }
    )
    records_df = records_df.dropna(subset=["id"])
    records_df = records_df.where(records_df.notna(), None)
    return records_df.to_dict("records")


def _upsert_movies(engine, records: list[dict]) -> int:
    if not records:
        return 0

    from sqlalchemy import MetaData, Table

    md = MetaData()
    movies = Table("movies", md, autoload_with=engine)

    # Keep safely below Postgres bind parameter limit (~65535)
    cols_per_row = len(records[0])
    max_params = 65000  # safety margin
    max_rows = max(1, (max_params // cols_per_row) - 1)

    total = 0
    with engine.begin() as conn:
        for i in range(0, len(records), max_rows):
            batch = records[i : i + max_rows]

            stmt = pg_insert(movies).values(batch)
            update_cols = {c.name: getattr(stmt.excluded, c.name) for c in movies.columns if c.name != "id"}
            stmt = stmt.on_conflict_do_update(index_elements=["id"], set_=update_cols)

            conn.execute(stmt)
            total += len(batch)

    return total

def main() -> None:
    _setup_logging()
    s = _load_settings()

    if not s.csv_path.exists():
        raise FileNotFoundError(f"CSV not found at: {s.csv_path}")

    logger.info("ingest_start csv_path=%s target_rows=%s chunksize=%s lang=en", s.csv_path, s.target_rows, s.chunksize)

    logger.info("pass_start pass=1")
    top_rated_ids, eligible_rows = _select_top_rated_ids(s.csv_path, s.chunksize, s.target_rows)
    logger.info("pass_complete pass=1 eligible_rows=%s selected_ids=%s", eligible_rows, len(top_rated_ids))

    engine = create_engine(s.database_url, hide_parameters=True)

    total_rows_seen = 0
    total_records_written = 0

    logger.info("pass_start pass=2")
    for df in _iter_recent_rows(s.csv_path, top_rated_ids, s.chunksize):
        total_rows_seen += len(df)
        records = _prepare_records(df)
        records = _dedupe_records(records)

        written = _upsert_movies(engine, records)
        total_records_written += len(records)
        logger.info(
            "chunk_processed rows_matched=%s records_prepared=%s records_written=%s total_written=%s",
            len(df),
            len(records),
            written,
            total_records_written,
        )

        # Stop early once we have written target_rows (some ids might be missing dates, duplicates, etc.)
        if total_records_written >= s.target_rows:
            break

    logger.info("ingest_complete records_written=%s", total_records_written)


if __name__ == "__main__":
    main()
