"""Olympics fetcher — news via ESPN."""

import logging
from datetime import datetime, timezone

from src.fetch.espn import espn, SportEvent

logger = logging.getLogger(__name__)


def fetch_olympics(config: dict, date_range: str) -> list[SportEvent]:
    """Fetch Olympics-related news as events."""
    events: list[SportEvent] = []
    articles = espn.news("olympics", "summer", limit=5)
    for a in articles:
        title = a.get("headline", "")
        if title:
            events.append(SportEvent(
                sport="Jeux Olympiques",
                league="JO",
                league_emoji="🏅",
                date=datetime.now(tz=timezone.utc),
                title=title,
                status="upcoming",
                is_must_watch=True,
            ))
    return events


def fetch_olympics_news(config: dict) -> list[dict]:
    articles = espn.news("olympics", "summer", limit=5)
    return [{"title": a.get("headline", ""), "url": a.get("links", {}).get("web", {}).get("href", "")} for a in articles]
