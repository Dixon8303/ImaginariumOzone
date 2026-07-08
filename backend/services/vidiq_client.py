"""
vidIQ client — real YouTube intelligence for P1 scoring, G4 benchmarks,
SEO enrichment, and the Discovery feed.

Requires VIDIQ_API_KEY in .env (from vidiq.com account settings).
Every function degrades gracefully: returns None/[] when the key is
missing or a call fails, and the pipeline continues on Claude-only data.
"""

import json
import config

try:
    import aiohttp
    _AIOHTTP_AVAILABLE = True
except ImportError:
    _AIOHTTP_AVAILABLE = False


def is_configured() -> bool:
    return bool(config.VIDIQ_API_KEY) and _AIOHTTP_AVAILABLE


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {config.VIDIQ_API_KEY}",
        "Content-Type": "application/json",
    }


async def _get(path: str, params: dict = None) -> dict | None:
    if not is_configured():
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{config.VIDIQ_BASE_URL}{path}",
                params=params, headers=_headers(),
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()
    except Exception:
        return None


async def _post(path: str, payload: dict) -> dict | None:
    if not is_configured():
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{config.VIDIQ_BASE_URL}{path}",
                json=payload, headers=_headers(),
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()
    except Exception:
        return None


async def keyword_research(keyword: str, country: str = "US") -> dict | None:
    """
    Real search volume + competition for a keyword.
    Returns {keyword, search_volume, competition, overall_score,
             related: [{keyword, search_volume, competition}]} or None.
    """
    data = await _get("/v0/keywords/research",
                      params={"keyword": keyword, "country": country})
    if not data:
        return None
    return {
        "keyword": keyword,
        "search_volume": data.get("search_volume") or data.get("volume"),
        "competition": data.get("competition"),
        "overall_score": data.get("overall_score") or data.get("score"),
        "related": [
            {
                "keyword": r.get("keyword"),
                "search_volume": r.get("search_volume") or r.get("volume"),
                "competition": r.get("competition"),
            }
            for r in (data.get("related_keywords") or data.get("related") or [])[:10]
        ],
    }


async def score_title(title: str) -> dict | None:
    """
    CTR-predictive score for a video title.
    Returns {title, score, suggestions: [str]} or None.
    """
    data = await _post("/v0/titles/score", {"title": title, "type": "long"})
    if not data:
        return None
    return {
        "title": title,
        "score": data.get("score"),
        "suggestions": data.get("suggestions", []),
    }


async def score_titles(titles: list[str]) -> list[dict]:
    """Score a batch of title candidates. Skips failures."""
    results = []
    for t in titles:
        s = await score_title(t)
        if s:
            results.append(s)
    return results


async def generate_titles(topic: str, n: int = 5) -> list[str]:
    """vidIQ AI title generation — adds to the Ollama candidate pool."""
    data = await _post("/v0/titles/generate", {"topic": topic, "count": n})
    if not data:
        return []
    titles = data.get("titles", [])
    return [t if isinstance(t, str) else t.get("title", "") for t in titles][:n]


async def trending_videos(category: str = None, country: str = "US") -> list[dict]:
    """
    Trending videos, optionally filtered by category.
    Returns [{title, channel, views, published_at, video_id}].
    """
    params = {"country": country}
    if category:
        params["category"] = category
    data = await _get("/v0/videos/trending", params=params)
    if not data:
        return []
    videos = data.get("videos", data) if isinstance(data, dict) else data
    return [
        {
            "title": v.get("title"),
            "channel": v.get("channel_title") or v.get("channel"),
            "views": v.get("views") or v.get("view_count"),
            "published_at": v.get("published_at"),
            "video_id": v.get("video_id") or v.get("id"),
        }
        for v in videos[:20]
    ]


async def search_outliers(query: str, country: str = "US") -> list[dict]:
    """
    Outlier videos — small channels with breakout performance on a topic.
    The strongest topic-validation signal: proves audience demand exists
    independent of channel size.
    Returns [{title, channel, views, subscriber_count, outlier_score}].
    """
    data = await _get("/v0/videos/outliers",
                      params={"query": query, "country": country})
    if not data:
        return []
    videos = data.get("videos", data) if isinstance(data, dict) else data
    return [
        {
            "title": v.get("title"),
            "channel": v.get("channel_title") or v.get("channel"),
            "views": v.get("views") or v.get("view_count"),
            "subscriber_count": v.get("subscriber_count"),
            "outlier_score": v.get("outlier_score") or v.get("multiplier"),
            "video_id": v.get("video_id") or v.get("id"),
        }
        for v in videos[:15]
    ]


async def channel_analytics(channel_id: str = None) -> dict | None:
    """
    Pull channel performance for the War Room — replaces manual metric entry.
    Returns {views, ctr, avg_view_duration, subscribers_gained, top_videos} or None.
    """
    path = f"/v0/channels/{channel_id}/analytics" if channel_id else "/v0/channels/mine/analytics"
    data = await _get(path)
    if not data:
        return None
    return {
        "views": data.get("views"),
        "ctr": data.get("ctr") or data.get("click_through_rate"),
        "avg_view_duration": data.get("avg_view_duration"),
        "retention_pct": data.get("retention_pct") or data.get("avg_percentage_viewed"),
        "subscribers_gained": data.get("subscribers_gained"),
        "top_videos": data.get("top_videos", []),
    }
