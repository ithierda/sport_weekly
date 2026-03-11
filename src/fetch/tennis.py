"""Tennis fetcher — Grand Slams, Masters 1000, top players."""

import logging
import urllib.parse
from datetime import datetime, timezone

import feedparser

from src.fetch.espn import espn, SportEvent

logger = logging.getLogger(__name__)

# Top players to always highlight
TOP_PLAYERS = [
    "djokovic", "sinner", "alcaraz", "medvedev", "zverev",
    "rublev", "tsitsipas", "ruud", "fritz", "fils",
]

GRAND_SLAMS = ["australian open", "roland garros", "roland-garros", "wimbledon", "us open"]
MASTERS = ["indian wells", "miami open", "monte carlo", "madrid open", "rome", "canada",
           "cincinnati", "shanghai", "paris", "bnp paribas"]


def fetch_tennis(config: dict, date_range: str) -> list[SportEvent]:
    events: list[SportEvent] = []
    player_filter = [p.lower() for p in config.get("players", [])]

    # ESPN tennis scoreboard returns tournaments (not individual matches)
    for league_slug in ["atp", "wta"]:
        data = espn.scoreboard("tennis", league_slug)
        label = "ATP Tour" if league_slug == "atp" else "WTA Tour"

        for ev in data.get("events", []):
            name = ev.get("name", "")
            try:
                dt = datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
            except (KeyError, ValueError):
                dt = datetime.now(tz=timezone.utc)

            status_obj = ev.get("status", {}).get("type", {})
            completed = status_obj.get("completed", False)
            state = status_obj.get("state", "pre")
            status = "completed" if completed else ("in_progress" if state == "in" else "upcoming")

            name_lower = name.lower()
            is_gs = any(gs in name_lower for gs in GRAND_SLAMS)
            is_masters = any(m in name_lower for m in MASTERS)
            detail = "Grand Chelem" if is_gs else ("Masters 1000" if is_masters else "")

            events.append(SportEvent(
                sport="Tennis",
                league=label,
                league_emoji="🎾",
                date=dt,
                title=name,
                status=status,
                is_must_watch=is_gs or is_masters,
                details=detail,
            ))

    # Add player-specific match news from Google News
    all_players = list({p.lower() for p in player_filter} | {"fils", "djokovic", "sinner", "alcaraz"})
    events.extend(_fetch_tennis_match_news(all_players))

    return events


def _fetch_tennis_match_news(players: list[str]) -> list[SportEvent]:
    """Use Google News RSS to surface recent match results/previews for watched players."""
    events: list[SportEvent] = []
    seen_titles: set[str] = set()

    # Build a query targeting watched players + Arthur Fils
    highlight_players = list({p.lower() for p in players} | {"arthur fils", "fils"})
    query_parts = [f'"{p}"' for p in highlight_players[:4]]
    query = " OR ".join(query_parts) + " tennis"
    url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(query) + "&hl=fr&gl=FR&ceid=FR:fr"

    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:8]:
            title = entry.get("title", "")
            link = entry.get("link", "")
            if not title or title in seen_titles:
                continue
            # Strip source suffix like " - L'Équipe"
            clean_title = title.split(" - ")[0].strip() if " - " in title else title
            seen_titles.add(title)

            pub = entry.get("published_parsed")
            if pub:
                dt = datetime(*pub[:6], tzinfo=timezone.utc)
            else:
                dt = datetime.now(tz=timezone.utc)

            source = entry.get("source", {}).get("title", "")
            title_lower = clean_title.lower()
            is_fils = "fils" in title_lower
            events.append(SportEvent(
                sport="Tennis",
                league="ATP Tour",
                league_emoji="🎾",
                date=dt,
                title=f"📰 {clean_title}",
                status="upcoming",
                is_must_watch=is_fils,
                details=source,
            ))
    except Exception as e:
        logger.warning("Tennis Google News RSS failed: %s", e)

    return events


def fetch_tennis_news(config: dict) -> list[dict]:
    articles = espn.news("tennis", "atp", limit=5)
    return [{"title": a.get("headline", ""), "url": a.get("links", {}).get("web", {}).get("href", ""), "published": a.get("published", "")} for a in articles]
