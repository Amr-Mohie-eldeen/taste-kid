from datetime import date

from api.rerank.features import extract_year, parse_genres
from api.rerank.scorer import ScoringContext, score_candidate


def test_parse_genres():
    assert parse_genres("Action, Comedy") == {"action", "comedy"}
    assert parse_genres(None) == set()
    assert parse_genres("") == set()
    assert parse_genres("Drama") == {"drama"}


def test_extract_year():
    assert extract_year(date(2023, 1, 1)) == 2023
    assert extract_year("2023-01-01") == 2023
    assert extract_year("2023") == 2023
    assert extract_year(None) is None
    assert extract_year("invalid") is None


def test_score_candidate_same_language():
    anchor = ScoringContext(
        genres={"action"}, keywords=set(), style=set(), runtime=100, year=2000, language="en"
    )
    candidate = ScoringContext(
        genres={"action"}, keywords=set(), style=set(), runtime=100, year=2000, language="en"
    )
    # Same language should give a bonus
    score_same = score_candidate(
        anchor, candidate, distance=0.1, vote_count=100, max_vote_count=1000
    )

    candidate_diff = ScoringContext(
        genres={"action"}, keywords=set(), style=set(), runtime=100, year=2000, language="fr"
    )
    score_diff = score_candidate(
        anchor, candidate_diff, distance=0.1, vote_count=100, max_vote_count=1000
    )

    assert score_same > score_diff


def test_score_candidate_runtime_mismatch():
    anchor = ScoringContext(
        genres={"action"}, keywords=set(), style=set(), runtime=100, year=2000, language="en"
    )
    candidate_match = ScoringContext(
        genres={"action"}, keywords=set(), style=set(), runtime=100, year=2000, language="en"
    )
    candidate_mismatch = ScoringContext(
        genres={"action"},
        keywords=set(),
        style=set(),
        runtime=200,  # Large difference
        year=2000,
        language="en",
    )

    score_match = score_candidate(
        anchor, candidate_match, distance=0.1, vote_count=100, max_vote_count=1000
    )
    score_mismatch = score_candidate(
        anchor, candidate_mismatch, distance=0.1, vote_count=100, max_vote_count=1000
    )

    assert score_match > score_mismatch
