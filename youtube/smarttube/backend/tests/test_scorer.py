"""
test_scorer.py — Unit tests for SmartTube Phase 1 Scoring Engine
"""

import pytest
from scorer import (
    compute_relevance_score,
    compute_content_quality_score,
    compute_duration_score,
    compute_engagement_score,
    rank_videos
)
from models import RawVideoInput
from config import DEFAULT_SCORING_WEIGHTS, ScoringWeights


def test_weights_sum_to_one():
    weights = ScoringWeights()
    assert weights.validate_weights() is True


def test_relevance_score_exact_match():
    query = "Python Pandas for data analysis"
    title = "Python Pandas for Data Analysis - Full Course"
    desc = "Learn python pandas for data analysis today."
    score, reason = compute_relevance_score(query, title, desc)
    assert score >= 0.8
    assert "match" in reason.lower()


def test_relevance_score_irrelevant_query():
    query = "Python Pandas for data analysis"
    title = "Top 10 Best Gaming Laptops 2024"
    desc = "Reviewing GPUs and screens for gamers."
    score, reason = compute_relevance_score(query, title, desc)
    assert score <= 0.2


def test_duration_scoring():
    # 20 min tutorial should be optimal
    score_opt, reason_opt = compute_duration_score(20 * 60)
    assert score_opt == 1.0
    assert "Optimal" in reason_opt

    # 30 second clip should be penalized
    score_short, reason_short = compute_duration_score(30)
    assert score_short < 0.5


def test_rank_videos_reorders_correctly():
    query = "Python Pandas tutorial"
    videos = [
        RawVideoInput(
            id="irrelevant_1",
            title="Minecraft Survival episode 5",
            channel="GamerPro",
            description="Building a house in minecraft",
            duration_seconds=600,
            views=100000,
            original_rank=1
        ),
        RawVideoInput(
            id="relevant_1",
            title="Complete Python Pandas Tutorial for Beginners",
            channel="Tech With Tim",
            description="Learn how to use pandas dataframes in python step by step.",
            duration_seconds=1200,
            views=500000,
            original_rank=2
        )
    ]

    ranked_results, summary = rank_videos(query, videos, DEFAULT_SCORING_WEIGHTS)
    
    assert summary.total_analyzed == 2
    # The relevant video should be boosted to #1
    assert ranked_results[0].id == "relevant_1"
    assert ranked_results[0].final_score > ranked_results[1].final_score
    assert "Highly" in ranked_results[0].label or "Relevant" in ranked_results[0].label
