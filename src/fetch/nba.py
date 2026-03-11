"""NBA fetcher — league highlights & Wembanyama tracker."""

import logging
from src.fetch.espn import espn, SportEvent

logger = logging.getLogger(__name__)

# Wembanyama's team (San Antonio Spurs as of 2025-26 season)
WEMBY_TEAM = "San Antonio Spurs"


def fetch_nba(config: dict, date_range: str) -> list[SportEvent]:
    events: list[SportEvent] = []
    data = espn.scoreboard("basketball", "nba", date_range)
    all_events = espn.parse_events(data, "NBA", "NBA", "🏀")

    players = config.get("players", [])

    # Track Wembanyama: filter for his team's games
    wemby_events = []
    if any("wembanyama" in p.lower() for p in players):
        wemby_events = [e for e in all_events if WEMBY_TEAM.lower() in e.home_team.lower() or WEMBY_TEAM.lower() in e.away_team.lower()]
        for ev in wemby_events:
            ev.is_must_watch = True
            ev.details = "🇫🇷 Victor Wembanyama"

    if config.get("follow_league"):
        # Return all NBA games but prioritize big matchups
        big_teams = ["celtics", "lakers", "warriors", "nuggets", "knicks", "76ers", "bucks", "spurs"]
        for ev in all_events:
            teams_lower = f"{ev.home_team} {ev.away_team}".lower()
            if any(t in teams_lower for t in big_teams):
                ev.is_must_watch = True
        events.extend(all_events)
    else:
        events.extend(wemby_events)

    return events


def fetch_nba_news(config: dict) -> list[dict]:
    articles = espn.news("basketball", "nba", limit=5)
    results = []
    for a in articles:
        title = a.get("headline", "")
        url = a.get("links", {}).get("web", {}).get("href", "")
        # Prioritize Wembanyama news
        results.append({"title": title, "url": url, "published": a.get("published", ""), "priority": "wembanyama" in title.lower()})
    return sorted(results, key=lambda x: x.get("priority", False), reverse=True)[:5]
