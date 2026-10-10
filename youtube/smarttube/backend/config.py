"""
config.py — SmartTube Scoring Weights and System Configuration

Exposes scoring weights as a configurable object for easy tuning and customization.
"""

from typing import Dict
from pydantic import BaseModel, Field


class ScoringWeights(BaseModel):
    """
    Scoring weights breakdown (Total: 1.0 / 100%)
    - Relevance to search query: 35%
    - Content quality signals: 25%
    - Engagement (views/recency adjusted): 15%
    - Freshness: 10%
    - Duration suitability: 10%
    - User preference match: 5%
    """
    relevance_query: float = Field(default=0.35, description="Semantic or keyword match to user query")
    content_quality: float = Field(default=0.25, description="Title clarity, description depth, creator signals")
    engagement: float = Field(default=0.15, description="Normalized view count & engagement momentum")
    freshness: float = Field(default=0.10, description="Recency score based on publish date")
    duration_suitability: float = Field(default=0.10, description="Suitability of video length for educational depth")
    user_preference: float = Field(default=0.05, description="Match to user skill level and history")

    def validate_weights(self) -> bool:
        total = (
            self.relevance_query
            + self.content_quality
            + self.engagement
            + self.freshness
            + self.duration_suitability
            + self.user_preference
        )
        return abs(total - 1.0) < 1e-4


# Global default configuration instance
DEFAULT_SCORING_WEIGHTS = ScoringWeights()

# Label classification thresholds
TIER_THRESHOLDS = {
    "HIGH": 0.70,     # >= 70% -> 🔥 Highly Relevant
    "RELEVANT": 0.45, # >= 45% -> ✅ Relevant
    # < 45% -> 📌 Other
}

# Preferred duration window in seconds for educational/technical topics (default: 8 to 45 mins)
DEFAULT_IDEAL_MIN_DURATION_SEC = 8 * 60    # 480 seconds (8 min)
DEFAULT_IDEAL_MAX_DURATION_SEC = 45 * 60   # 2700 seconds (45 min)
