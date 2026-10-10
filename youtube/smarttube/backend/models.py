"""
models.py — Pydantic Request & Response Data Schemas
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RawVideoInput(BaseModel):
    id: str
    title: str
    channel: str = "Unknown Channel"
    description: str = ""
    duration_seconds: int = 0
    duration_formatted: str = "0:00"
    views: int = 0
    views_formatted: str = "0 views"
    published_text: str = "recently"
    thumbnail_url: str = ""
    url: str = ""
    original_rank: int = 1


class RankRequest(BaseModel):
    query: str
    videos: List[RawVideoInput]
    api_key: Optional[str] = None
    custom_weights: Optional[Dict[str, float]] = None


class RankedVideoItem(BaseModel):
    id: str
    title: str
    channel: str
    description: str
    duration_seconds: int
    duration_formatted: str
    views: int
    views_formatted: str
    published_text: str
    thumbnail_url: str
    url: str
    original_rank: int
    
    # SmartTube Computed Scores
    final_score: float = Field(..., description="Overall weighted score normalized 0.0 to 1.0")
    label: str = Field(..., description="'🔥 Highly Relevant' | '✅ Relevant' | '📌 Other'")
    explanation: str = Field(..., description="Concise explanation for why the video was ranked here")
    sub_scores: Dict[str, float] = Field(default_factory=dict, description="Component score breakdown")


class SummaryStatistics(BaseModel):
    total_analyzed: int
    tier_counts: Dict[str, int]
    total_watch_time_seconds: int
    avg_score: float


class RankResponse(BaseModel):
    query: str
    results: List[RankedVideoItem]
    summary: SummaryStatistics
