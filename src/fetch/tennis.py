"""Tennis fetcher — Grand Slams, Masters 1000, top players."""

import logging
from datetime import datetime, timezone
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

    # Check news for player-specific updates
    articles = espn.news("tennis", "atp", limit=10)
    for a in articles:
        headline = a.get("headline", "").lower()
        if player_filter and any(p in headline for p in player_filter):
            events.append(SportEvent(
                sport="Tennis",
                league="ATP Tour",
                league_emoji="🎾",
                date=datetime.now(tz=timezone.utc),
                title=f"📰 {a.get('headline', '')}",
                status="upcoming",
                is_must_watch=True,
                details="⭐ Joueur suivi",
            ))

    return events


def fetch_tennis_news(config: dict) -> list[dict]:
    articles = espn.news("tennis", "atp", limit=5)
    return [{"title": a.get("headline", ""), "url": a.get("links", {}).get("web", {}).get("href", ""), "published": a.get("published", "")} for a in articles]
