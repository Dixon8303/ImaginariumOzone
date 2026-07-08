"""
Discovery feed — "What to Make Next".

Combines:
  - vidIQ outliers/trending (real audience-demand signals, when configured)
  - Haiku-generated BGF topic candidates (always available)
  - vidIQ keyword research passthrough for the New Episode form
  - vidIQ channel analytics pull for the War Room
"""

import json
from fastapi import APIRouter, HTTPException
import config

router = APIRouter(prefix="/api/discovery", tags=["discovery"])

# Seed queries that define the BGF content space for outlier searches
BGF_SEED_QUERIES = [
    "black history documentary",
    "black inventors erased history",
    "black wall street",
    "freedmen's bureau",
    "black wealth history",
]


@router.get("/feed")
async def discovery_feed():
    """Topic ideas: vidIQ outliers per seed query + Haiku BGF candidates."""
    from services import vidiq_client, claude_client

    outliers = []
    if vidiq_client.is_configured():
        for q in BGF_SEED_QUERIES[:3]:
            results = await vidiq_client.search_outliers(q)
            for r in results[:5]:
                r["seed_query"] = q
                outliers.append(r)

    # Haiku topic candidates — always available, shaped by the production bible
    system = claude_client._load_bible()
    user = (
        "Generate 6 episode topic candidates for The Black Genius Files.\n"
        "Each must: name a real institution or documented individual, "
        "frame through systems (not lone-genius narrative), and be "
        "reconstructable from primary sources.\n\n"
        "Return JSON array: [{\"topic\": str, \"hook\": str (one sentence), "
        "\"era\": str, \"primary_keyword\": str}]"
    )
    try:
        raw = await claude_client.complete_with_model(
            config.MODEL_HAIKU, system, user, max_tokens=1500)
        candidates = claude_client._parse_json(raw, "discovery")
    except Exception:
        candidates = []

    return {
        "vidiq_configured": vidiq_client.is_configured(),
        "outliers": outliers,
        "candidates": candidates,
    }


@router.get("/keyword/{keyword}")
async def keyword_lookup(keyword: str):
    """Real search volume + competition for the New Episode form."""
    from services import vidiq_client
    if not vidiq_client.is_configured():
        return {"configured": False, "data": None}
    data = await vidiq_client.keyword_research(keyword)
    return {"configured": True, "data": data}


@router.get("/analytics")
async def channel_analytics():
    """Live channel performance for the War Room — replaces manual entry."""
    from services import vidiq_client
    if not vidiq_client.is_configured():
        return {"configured": False, "data": None}
    data = await vidiq_client.channel_analytics(
        config.YOUTUBE_CHANNEL_ID or None)
    return {"configured": True, "data": data}
