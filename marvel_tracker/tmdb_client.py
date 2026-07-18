"""Thin wrapper around the parts of the TMDb API this tracker needs.

TMDb has no single "everything Marvel Studios" endpoint, so coverage is built
from two pieces:
  - /discover/movie and /discover/tv filtered by Marvel Studios' company id,
    which catches nearly everything TMDb has tagged correctly.
  - Per-show season/episode lookups (including season 0, "Specials") for
    every Marvel Studios show, so individual episodes and one-off specials
    show up as their own trackable items, not just the show's premiere.

`tracked_ids.yaml` lets a human fill in anything the company filter misses,
or exclude false positives.
"""

import requests

from . import config

_session = requests.Session()


def _get(path, params=None):
    params = dict(params or {})
    params["api_key"] = config.TMDB_API_KEY
    response = _session.get(f"{config.TMDB_BASE_URL}{path}", params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def _discover_all_pages(media_type, extra_ids=None, excluded_ids=None):
    """Return TMDb ids for every movie/show tagged with Marvel Studios."""
    ids = set(extra_ids or [])
    page = 1
    total_pages = 1
    while page <= total_pages:
        data = _get(
            f"/discover/{media_type}",
            params={
                "with_companies": config.MARVEL_STUDIOS_COMPANY_ID,
                "page": page,
                "sort_by": "primary_release_date.desc"
                if media_type == "movie"
                else "first_air_date.desc",
            },
        )
        ids.update(result["id"] for result in data.get("results", []))
        total_pages = data.get("total_pages", 1)
        page += 1
    return ids - set(excluded_ids or [])


def fetch_movies(extra_ids=None, excluded_ids=None):
    """Return normalized items for every tracked Marvel Studios movie/short."""
    items = []
    for movie_id in _discover_all_pages("movie", extra_ids, excluded_ids):
        detail = _get(f"/movie/{movie_id}")
        items.append(
            {
                "item_id": f"movie-{movie_id}",
                "kind": "movie",
                "title": detail.get("title") or detail.get("original_title"),
                "date": detail.get("release_date") or None,
                "parent_show": None,
            }
        )
    return items


def fetch_show_episodes(extra_ids=None, excluded_ids=None):
    """Return normalized items for every episode/special of every tracked show."""
    items = []
    for show_id in _discover_all_pages("tv", extra_ids, excluded_ids):
        show = _get(f"/tv/{show_id}")
        show_name = show.get("name")
        for season in show.get("seasons", []):
            season_number = season["season_number"]
            season_detail = _get(f"/tv/{show_id}/season/{season_number}")
            for episode in season_detail.get("episodes", []):
                kind = "special" if season_number == 0 else "episode"
                items.append(
                    {
                        "item_id": f"{kind}-{show_id}-{season_number}-{episode['episode_number']}",
                        "kind": kind,
                        "title": f"{show_name}: {episode.get('name')}",
                        "date": episode.get("air_date") or None,
                        "parent_show": show_name,
                    }
                )
    return items


def fetch_all_items(tracked_ids):
    movies = fetch_movies(
        tracked_ids.get("extra_movie_ids"), tracked_ids.get("excluded_movie_ids")
    )
    episodes = fetch_show_episodes(
        tracked_ids.get("extra_show_ids"), tracked_ids.get("excluded_show_ids")
    )
    return movies + episodes
