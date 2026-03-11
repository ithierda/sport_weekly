"""F1 & MotoGP fetcher."""

import logging
from datetime import datetime, timezone

import requests
import feedparser

from src.fetch.espn import espn, SportEvent

logger = logging.getLogger(__name__)

MOTOGP_RSS = "https://www.motogp.com/en/rss/news"


def fetch_f1(config: dict, date_range: str) -> list[SportEvent]:
    data = espn.scoreboard("racing", "f1", date_range)
    events = espn.parse_events(data, "F1", "Formule 1", "🏎️")
    for ev in events:
        ev.is_must_watch = True  # Every F1 race weekend is must-watch
    return events


def fetch_motogp(config: dict, date_range: str) -> list[SportEvent]:
    """Fetch MotoGP events — ESPN doesn't support MotoGP, use RSS/news."""
    events: list[SportEvent] = []
    try:
        r = requests.get(MOTOGP_RSS, headers={"User-Agent": "SportWeekly/1.0"}, timeout=15)
        r.raise_for_status()
        feed = feedparser.parse(r.text)
        for entry in feed.entries[:5]:
            title = entry.get("title", "")
            if any(kw in title.lower() for kw in ["race", "gp", "grand prix", "qualifying", "sprint"]):
                events.append(SportEvent(
                    sport="MotoGP",
                    league="MotoGP",
                    league_emoji="🏍️",
                    date=datetime.now(tz=timezone.utc),
                    title=title,
                    status="upcoming",
                    is_must_watch=True,
                ))
    except Exception as e:
        logger.warning("MotoGP RSS failed: %s", e)
    return events


def fetch_motorsport_news(config: dict) -> list[dict]:
    articles = espn.news("racing", "f1", limit=5)
    return [{"title": a.get("headline", ""), "url": a.get("links", {}).get("web", {}).get("href", "")} for a in articles]
