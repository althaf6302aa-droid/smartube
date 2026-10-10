"""
scorer.py — SmartTube Non-ML Baseline Scoring Engine (Phase 1)

Implements weighted scoring pipeline:
1. Relevance to search query (35%)
2. Content quality signals (25%)
3. Engagement (views/recency adjusted) (15%)
4. Freshness (10%)
5. Duration suitability (10%)
6. User preference match (5%)
"""

import re
import math
from typing import List, Tuple, Dict
from models import RawVideoInput, RankedVideoItem, SummaryStatistics
from config import ScoringWeights, DEFAULT_SCORING_WEIGHTS, TIER_THRESHOLDS, DEFAULT_IDEAL_MIN_DURATION_SEC, DEFAULT_IDEAL_MAX_DURATION_SEC


def tokenize(text: str) -> set:
    """Normalize and tokenize text into unique words."""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return set(w for w in cleaned.split() if len(w) > 1)


def compute_relevance_score(query: str, title: str, description: str) -> Tuple[float, str]:
    """
    Computes query-to-content relevance score in [0.0, 1.0].
    Gives heavy weight to title match and exact query phrase matching.
    """
    q_tokens = tokenize(query)
    if not q_tokens:
        return 0.5, "Query was generic"

    title_tokens = tokenize(title)
    desc_tokens = tokenize(description)

    # Token overlap (Jaccard / coverage)
    title_overlap = len(q_tokens.intersection(title_tokens)) / len(q_tokens)
    desc_overlap = len(q_tokens.intersection(desc_tokens)) / len(q_tokens) if desc_tokens else 0.0

    # Exact phrase match bonus
    norm_query = query.lower().strip()
    norm_title = title.lower()
    norm_desc = description.lower()

    exact_title_match = 1.0 if norm_query in norm_title else 0.0
    exact_desc_match = 1.0 if norm_query in norm_desc else 0.0

    # Weighted combination
    score = (
        0.50 * title_overlap
        + 0.25 * exact_title_match
        + 0.15 * desc_overlap
        + 0.10 * exact_desc_match
    )
    score = min(1.0, max(0.0, score))

    if exact_title_match:
        reason = "Exact query match in title"
    elif title_overlap >= 0.75:
        reason = "High keyword overlap with title"
    elif title_overlap >= 0.4:
        reason = "Moderate keyword match"
    else:
        reason = "Low title/description keyword match"

    return score, reason


def compute_content_quality_score(title: str, description: str, channel: str) -> float:
    """
    Heuristic quality scoring:
    - Informative title length (not too short, not purely spammy)
    - Penalty for all-caps clickbait
    - Reward for comprehensive description
    """
    score = 0.5

    # Title length check
    if 25 <= len(title) <= 90:
        score += 0.2
    elif len(title) < 15:
        score -= 0.2

    # Clickbait check: excessive uppercase letters
    letters = [c for c in title if c.isalpha()]
    if letters:
        upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
        if upper_ratio > 0.65 and len(letters) > 15:
            score -= 0.25  # All caps penalty
        elif 0.05 <= upper_ratio <= 0.35:
            score += 0.1

    # Description depth
    if len(description) > 60:
        score += 0.15
    elif len(description) == 0:
        score -= 0.1

    # Recognized channel string
    if channel and channel != "Unknown Channel":
        score += 0.05

    return min(1.0, max(0.1, score))


def compute_engagement_score(views: int) -> float:
    """
    Log-normalized view score.
    1k views -> ~0.3
    50k views -> ~0.65
    500k views -> ~0.85
    5M+ views -> 1.0
    """
    if views <= 0:
        return 0.1
    
    # Log scale up to 5,000,000 views
    log_v = math.log10(views + 1)
    # log10(1) = 0, log10(1,000) = 3, log10(5,000,000) = 6.7
    score = log_v / 6.7
    return min(1.0, max(0.05, score))


def compute_freshness_score(published_text: str) -> float:
    """
    Estimates freshness from relative text (e.g., '2 days ago', '3 months ago', '4 years ago').
    """
    text = published_text.lower()
    
    if "hour" in text or "day" in text or "week" in text:
        return 1.0
    elif "month" in text:
        # Check number of months
        match = re.search(r"(\d+)\s*month", text)
        if match:
            months = int(match.group(1))
            return max(0.5, 1.0 - (months * 0.05))
        return 0.8
    elif "year" in text:
        match = re.search(r"(\d+)\s*year", text)
        if match:
            years = int(match.group(1))
            return max(0.1, 0.6 - (years * 0.12))
        return 0.4
    elif "stream" in text or "live" in text:
        return 0.95
    return 0.5


def compute_duration_score(duration_seconds: int) -> Tuple[float, str]:
    """
    Scores duration suitability for technical and educational tutorials:
    - Ideal: 8 min to 45 min (0.9 - 1.0)
    - Short clip: < 2 min (0.3 - 0.5)
    - Very long: > 3 hours (0.6)
    """
    if duration_seconds <= 0:
        return 0.5, "Standard duration"

    if DEFAULT_IDEAL_MIN_DURATION_SEC <= duration_seconds <= DEFAULT_IDEAL_MAX_DURATION_SEC:
        return 1.0, "Optimal tutorial length"
    elif duration_seconds < 120:  # Under 2 mins (shorts or tiny clips)
        return 0.35, "Very brief clip"
    elif duration_seconds < DEFAULT_IDEAL_MIN_DURATION_SEC:
        return 0.75, "Concise overview"
    elif duration_seconds <= 120 * 60:  # 45 min to 2 hours
        return 0.85, "Comprehensive deep dive"
    else:  # Over 2 hours
        return 0.6, "Very long full course"


def generate_explanation(
    relevance_reason: str,
    duration_reason: str,
    views: int,
    freshness_score: float,
    final_score: float
) -> str:
    """Generates an intuitive natural language explanation for why the video was ranked here."""
    points = [relevance_reason]

    if duration_reason in ["Optimal tutorial length", "Comprehensive deep dive"]:
        points.append(duration_reason.lower())

    if views > 100_000:
        points.append("strong community viewership")
    elif freshness_score >= 0.85:
        points.append("recent upload")

    joined = ", ".join(points)
    return f"{joined.capitalize()} (score: {int(final_score * 100)}%)."


def rank_videos(
    query: str,
    raw_videos: List[RawVideoInput],
    weights: ScoringWeights = DEFAULT_SCORING_WEIGHTS
) -> Tuple[List[RankedVideoItem], SummaryStatistics]:
    """
    Ranks the batch of videos according to the weighted matrix formula.
    """
    ranked_list: List[RankedVideoItem] = []
    tier_counts = {"🔥 Highly Relevant": 0, "✅ Relevant": 0, "📌 Other": 0}
    total_watch_time = 0
    total_score = 0.0

    for video in raw_videos:
        # 1. Relevance Score (35%)
        rel_score, rel_reason = compute_relevance_score(query, video.title, video.description)

        # 2. Content Quality (25%)
        qual_score = compute_content_quality_score(video.title, video.description, video.channel)

        # 3. Engagement (15%)
        eng_score = compute_engagement_score(video.views)

        # 4. Freshness (10%)
        fresh_score = compute_freshness_score(video.published_text)

        # 5. Duration Suitability (10%)
        dur_score, dur_reason = compute_duration_score(video.duration_seconds)

        # 6. User Preference (5%) - baseline default
        pref_score = 0.7

        # Weighted final score
        final_score = (
            weights.relevance_query * rel_score
            + weights.content_quality * qual_score
            + weights.engagement * eng_score
            + weights.freshness * fresh_score
            + weights.duration_suitability * dur_score
            + weights.user_preference * pref_score
        )
        final_score = round(min(1.0, max(0.0, final_score)), 4)
        total_score += final_score

        # Determine Tier Label
        if final_score >= TIER_THRESHOLDS["HIGH"]:
            label = "🔥 Highly Relevant"
        elif final_score >= TIER_THRESHOLDS["RELEVANT"]:
            label = "✅ Relevant"
        else:
            label = "📌 Other"

        tier_counts[label] += 1
        total_watch_time += video.duration_seconds

        explanation = generate_explanation(
            rel_reason,
            dur_reason,
            video.views,
            fresh_score,
            final_score
        )

        sub_scores = {
            "relevance": round(rel_score, 3),
            "quality": round(qual_score, 3),
            "engagement": round(eng_score, 3),
            "freshness": round(fresh_score, 3),
            "duration": round(dur_score, 3),
            "user_preference": round(pref_score, 3),
        }

        ranked_list.append(RankedVideoItem(
            id=video.id,
            title=video.title,
            channel=video.channel,
            description=video.description,
            duration_seconds=video.duration_seconds,
            duration_formatted=video.duration_formatted,
            views=video.views,
            views_formatted=video.views_formatted,
            published_text=video.published_text,
            thumbnail_url=video.thumbnail_url,
            url=video.url,
            original_rank=video.original_rank,
            final_score=final_score,
            label=label,
            explanation=explanation,
            sub_scores=sub_scores
        ))

    # Sort descending by final_score
    ranked_list.sort(key=lambda x: x.final_score, reverse=True)

    avg_score = round(total_score / len(raw_videos), 4) if raw_videos else 0.0

    summary = SummaryStatistics(
        total_analyzed=len(raw_videos),
        tier_counts=tier_counts,
        total_watch_time_seconds=total_watch_time,
        avg_score=avg_score
    )

    return ranked_list, summary
