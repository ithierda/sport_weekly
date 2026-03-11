"""Football (Soccer) fetcher — Champions League & PSG."""

import logging
from datetime import datetime
from src.fetch.espn import espn, SportEvent

logger = logging.getLogger(__name__)

LEAGUES = {
    "champions_league": ("soccer", "uefa.champions", "Champions League", "⚽"),
    "ligue_1": ("soccer", "fra.1", "Ligue 1", "⚽"),
}


def fetch_football(config: dict, date_range: str) -> list[SportEvent]:
    """Fetch football events for the week."""
    events: list[SportEvent] = []
    leagues = config.get("leagues", [])
    teams = config.get("teams", [])

    for league_key in leagues:
        if league_key == "champions_league":
            sport, slug, label, emoji = LEAGUES["champions_league"]
            data = espn.scoreboard(sport, slug, date_range)
            events.extend(espn.parse_events(data, "Football", label, emoji))
        elif league_key == "ligue_1":
            sport, slug, label, emoji = LEAGUES["ligue_1"]
            data = espn.scoreboard(sport, slug, date_range)
            events.extend(espn.parse_events(data, "Football", label, emoji, team_filter=teams))

    # If user follows teams and has champions_league, also check Ligue 1 for PSG etc.
    if "champions_league" in leagues and teams and "ligue_1" not in leagues:
        sport, slug, label, emoji = LEAGUES["ligue_1"]
        data = espn.scoreboard(sport, slug, date_range)
        events.extend(espn.parse_events(data, "Football", label, emoji, team_filter=teams))

    return events


def fetch_football_news(config: dict) -> list[dict]:
    articles = espn.news("soccer", "uefa.champions", limit=5)
    return [{"title": a.get("headline", ""), "url": a.get("links", {}).get("web", {}).get("href", "")} for a in articles]
