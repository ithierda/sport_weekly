"""F1 & MotoGP fetcher."""

import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests
import feedparser

from src.fetch.espn import espn, SportEvent

logger = logging.getLogger(__name__)

MOTOGP_RSS = "https://www.motogp.com/en/rss/news"
PARIS_TZ = ZoneInfo("Europe/Paris")

# Map ESPN F1 competition type abbreviations to French labels
F1_SESSION_LABELS = {
    "FP1": "Essais Libres 1",
    "FP2": "Essais Libres 2",
    "FP3": "Essais Libres 3",
    "Qual": "Qualifications",
    "Sprint": "Sprint Shootout",
    "SR": "Course Sprint",
    "Race": "Course",
}


def fetch_f1(config: dict, date_range: str) -> list[SportEvent]:
    data = espn.scoreboard("racing", "f1", date_range)
    events: list[SportEvent] = []

    for ev in data.get("events", []):
        event_name = ev.get("name", ev.get("shortName", ""))
        circuit = ev.get("circuit", {}).get("fullName", "")

        for comp in ev.get("competitions", []):
            comp_type = comp.get("type", {})
            abbr = comp_type.get("abbreviation", "")
            session_label = F1_SESSION_LABELS.get(abbr, abbr)

            try:
                dt = datetime.fromisoformat(comp["date"].replace("Z", "+00:00")).astimezone(PARIS_TZ)
            except (KeyError, ValueError):
                continue

            status_obj = comp.get("status", {}).get("type", {})
            completed = status_obj.get("completed", False)
            state = status_obj.get("state", "pre")
            status = "completed" if completed else ("in_progress" if state == "in" else "upcoming")

            # Only the Race is must-watch (to avoid flooding top 5 with 5 F1 sessions)
            is_must = abbr == "Race"

            events.append(SportEvent(
                sport="F1",
                league="Formule 1",
                league_emoji="🏎️",
                date=dt,
                title=f"{event_name} — {session_label}",
                status=status,
                venue=circuit,
                is_must_watch=is_must,
                details=circuit if circuit else "",
                round_info=session_label,
            ))

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
    return [{"title": a.get("headline", ""), "url": a.get("links", {}).get("web", {}).get("href", ""), "published": a.get("published", "")} for a in articles]
