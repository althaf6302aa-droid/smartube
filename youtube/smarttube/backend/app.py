"""
app.py — SmartTube FastAPI Ranking Service

Entry point for local and hosted backend execution.
Run locally via:
  uvicorn app:app --reload --port 8000
"""

import time
import logging
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from models import RankRequest, RankResponse
from scorer import rank_videos
from config import ScoringWeights, DEFAULT_SCORING_WEIGHTS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SmartTubeBackend")

app = FastAPI(
    title="SmartTube Intelligent Re-Ranking Engine",
    description="Backend API for SmartTube Chrome Extension to score & rank YouTube search results.",
    version="1.0.0"
)

# Allow Chrome Extension cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint used by the extension popup to verify server connectivity."""
    return {
        "status": "online",
        "service": "SmartTube Ranking API",
        "version": "1.0.0",
        "timestamp": time.time()
    }


@app.post("/rank", response_model=RankResponse, status_code=status.HTTP_200_OK)
async def rank_endpoint(request: RankRequest):
    """
    Ranks a list of videos scraped from the YouTube search results DOM.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty."
        )

    if not request.videos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No videos provided in request payload."
        )

    logger.info(f"Received ranking request for query='{request.query}' with {len(request.videos)} videos.")

    # Check for custom weights if provided
    weights = DEFAULT_SCORING_WEIGHTS
    if request.custom_weights:
        try:
            weights = ScoringWeights(**request.custom_weights)
        except Exception as e:
            logger.warning(f"Invalid custom weights provided: {e}. Falling back to default.")

    # Run ranking engine
    ranked_results, summary = rank_videos(
        query=request.query,
        raw_videos=request.videos,
        weights=weights
    )

    logger.info(f"Completed ranking. High: {summary.tier_counts.get('🔥 Highly Relevant', 0)}, "
                f"Relevant: {summary.tier_counts.get('✅ Relevant', 0)}, "
                f"Other: {summary.tier_counts.get('📌 Other', 0)}")

    return RankResponse(
        query=request.query,
        results=ranked_results,
        summary=summary
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
