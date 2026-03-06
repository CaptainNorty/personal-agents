import hashlib
import html
import re
import time
from difflib import SequenceMatcher

import httpx
from loguru import logger

from app.config import settings

SPOTIFY_OEMBED_URL = "https://open.spotify.com/oembed"
PODCASTINDEX_BASE = "https://api.podcastindex.org/api/1.0"
TITLE_MATCH_THRESHOLD = 0.4


async def resolve_spotify_url(url: str) -> tuple[str, str, str]:
    """Resolve a Spotify episode URL to a direct audio (MP3) URL.

    Returns (audio_url, show_name, episode_title).
    Raises ValueError if resolution fails at any step.
    """
    show_name, episode_title = await _get_spotify_metadata(url)
    logger.info(f"Spotify metadata: '{episode_title}' from '{show_name}'")

    feed_id = await _search_podcast_feed(show_name)
    audio_url = await _find_episode_audio(feed_id, episode_title)
    return audio_url, show_name, episode_title


async def _get_spotify_metadata(url: str) -> tuple[str, str]:
    """Fetch episode metadata from Spotify.

    Returns (show_name, episode_title).
    Uses oEmbed first; falls back to page meta tags if the oEmbed title
    doesn't contain the "Episode - Show" separator.
    """
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.get(SPOTIFY_OEMBED_URL, params={"url": url})
        resp.raise_for_status()
        data = resp.json()

        title = html.unescape(data.get("title", ""))

        # oEmbed sometimes returns "Episode Title - Podcast Name"
        if " - " in title:
            episode_title, show_name = title.rsplit(" - ", 1)
            return show_name.strip(), episode_title.strip()

        # Otherwise title is just the episode name — scrape the page for the show name
        episode_title = title
        logger.debug(f"oEmbed title has no separator, fetching page for show name: {url}")
        show_name = await _get_show_name_from_page(client, url)
        return show_name, episode_title


async def _get_show_name_from_page(client: httpx.AsyncClient, url: str) -> str:
    """Extract the podcast/show name from a Spotify episode page's meta tags."""
    resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    page_html = resp.text

    # og:description typically: "Listen to this episode from <Show Name> on Spotify. ..."
    match = re.search(r'content="[^"]*?\bfrom (.+?) on Spotify', page_html)
    if match:
        return html.unescape(match.group(1).strip())

    # Fallback: <title> tag often "Episode Title · Show Name | Podcast on Spotify"
    match = re.search(r"<title>.*?·\s*(.+?)\s*\|", page_html)
    if match:
        return html.unescape(match.group(1).strip())

    raise ValueError(
        "Could not determine podcast name from Spotify page — "
        "try sending the direct audio URL instead"
    )


def _podcastindex_auth_headers() -> dict[str, str]:
    """Generate PodcastIndex API authentication headers."""
    api_key = settings.podcastindex_api_key
    api_secret = settings.podcastindex_api_secret
    epoch_time = str(int(time.time()))
    sha_hash = hashlib.sha1(
        (api_key + api_secret + epoch_time).encode()
    ).hexdigest()

    return {
        "User-Agent": "PersonalAgents/1.0",
        "X-Auth-Key": api_key,
        "X-Auth-Date": epoch_time,
        "Authorization": sha_hash,
    }


async def _search_podcast_feed(name: str) -> int:
    """Search PodcastIndex for a podcast by name. Returns the feed ID.

    Picks the feed whose title best matches the show name rather than
    blindly taking the first result.
    """
    headers = _podcastindex_auth_headers()

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{PODCASTINDEX_BASE}/search/byterm",
            headers=headers,
            params={"q": name},
        )
        resp.raise_for_status()
        data = resp.json()

    feeds = data.get("feeds", [])
    if not feeds:
        raise ValueError(f"No podcast found on PodcastIndex for: '{name}'")

    # Pick the feed whose title is the closest match to the show name
    name_lower = name.lower()
    best_feed = feeds[0]
    best_ratio = 0.0
    for feed in feeds:
        feed_title = feed.get("title", "")
        ratio = SequenceMatcher(None, name_lower, feed_title.lower()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_feed = feed

    feed_id = best_feed["id"]
    logger.info(f"PodcastIndex feed match: {best_feed.get('title')} (id={feed_id}, {best_ratio:.0%} title similarity)")
    return feed_id


async def _find_episode_audio(feed_id: int, episode_title: str) -> str:
    """Fetch episodes for a feed and fuzzy-match the title to find the audio URL."""
    headers = _podcastindex_auth_headers()

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{PODCASTINDEX_BASE}/episodes/byfeedid",
            headers=headers,
            params={"id": feed_id, "max": 50},
        )
        resp.raise_for_status()
        data = resp.json()

    episodes = data.get("items", [])
    if not episodes:
        raise ValueError(f"No episodes found for feed {feed_id}")

    best_match = None
    best_ratio = 0.0
    episode_title_lower = episode_title.lower()

    for ep in episodes:
        ep_title = ep.get("title", "")
        ratio = SequenceMatcher(None, episode_title_lower, ep_title.lower()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = ep

    if best_match is None or best_ratio < TITLE_MATCH_THRESHOLD:
        raise ValueError(
            f"No matching episode found (best match: {best_ratio:.0%} similarity)"
        )

    audio_url = best_match.get("enclosureUrl", "")
    if not audio_url:
        raise ValueError(f"Matched episode '{best_match.get('title')}' has no audio URL")

    logger.info(
        f"Episode matched: '{best_match.get('title')}' ({best_ratio:.0%} similarity) → {audio_url}"
    )
    return audio_url
