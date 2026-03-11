"""Rugby fetcher — Top 14, Champions Cup, France, Sevens."""

import logging
from src.fetch.espn import espn, SportEvent

logger = logging.getLogger(__name__)

# ESPN rugby league slugs (numeric IDs)
LEAGUES = {
    "top14": ("rugby", "270559", "Top 14", "🏉"),
    "champions_cup": ("rugby", "271937", "Champions Cup", "🏉"),
    "six_nations": ("rugby", "180659", "Six Nations", "🏉"),
    "test_matches": ("rugby", "180659", "Six Nations", "🏉"),
    "sevens": ("rugby", "282", "World Rugby Sevens", "🏉"),
}


def fetch_rugby(config: dict, date_range: str) -> list[SportEvent]:
    events: list[SportEvent] = []
    leagues = config.get("leagues", [])
    teams = config.get("teams", [])

    for league_key in leagues:
        if league_key not in LEAGUES:
            logger.warning("Unknown rugby league: %s", league_key)
            continue
        sport, slug, label, emoji = LEAGUES[league_key]
        data = espn.scoreboard(sport, slug, date_range)
        # Don't filter by team — show all events for followed leagues
        parsed = espn.parse_events(data, "Rugby", label, emoji)
        # Mark favorite team matches as must-watch
        for ev in parsed:
            if teams and any(t.lower() in ev.title.lower() for t in teams):
                ev.is_must_watch = True
        events.extend(parsed)

    return events


def fetch_rugby_news(config: dict) -> list[dict]:
    articles = []
    for slug in ["270559", "271937"]:
        articles.extend(espn.news("rugby", slug, limit=3))
    return [{"title": a.get("headline", ""), "url": a.get("links", {}).get("web", {}).get("href", ""), "published": a.get("published", "")} for a in articles[:5]]
