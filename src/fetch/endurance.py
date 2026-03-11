"""Endurance sports — Trail, Running, Swimming, Athletics."""

import logging
from datetime import datetime, timedelta, timezone

import requests
import feedparser
from bs4 import BeautifulSoup

from src.fetch.espn import SportEvent

logger = logging.getLogger(__name__)

TIMEOUT = 30

# Major trail/ultra races calendar (well-known dates, stable year to year)
UTMB_URL = "https://utmb.world/events"
WORLD_ATHLETICS_RSS = "https://worldathletics.org/rss"
WORLD_AQUATICS_URL = "https://www.worldaquatics.com/competitions"

# Major marathon/running events (world's biggest)
MAJOR_MARATHONS = [
    "Marathon de Paris", "Marathon de Londres", "Marathon de Berlin",
    "Marathon de New York", "Marathon de Chicago", "Marathon de Tokyo",
    "Marathon de Boston",
]


def fetch_trail(config: dict, date_range: str) -> list[SportEvent]:
    """Fetch major trail/ultra events from UTMB World."""
    events: list[SportEvent] = []

    try:
        parts = date_range.split("-")
        start = datetime.strptime(parts[0], "%Y%m%d")
        end = datetime.strptime(parts[1], "%Y%m%d") if len(parts) > 1 else start + timedelta(days=7)
    except (ValueError, IndexError):
        start = datetime.now()
        end = start + timedelta(days=7)

    try:
        r = requests.get(
            UTMB_URL,
            headers={"User-Agent": "SportWeekly/1.0"},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        for item in soup.select(".race-card, .event-item, article"):
            title_el = item.select_one("h2, h3, .race-name, .title")
            date_el = item.select_one(".date, time, .race-date")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            date_str = date_el.get("datetime", date_el.get_text(strip=True)) if date_el else ""

            event_date = None
            for fmt in ["%Y-%m-%d", "%d %B %Y", "%d/%m/%Y", "%d %b %Y"]:
                try:
                    event_date = datetime.strptime(date_str.strip(), fmt).replace(tzinfo=timezone.utc)
                    break
                except ValueError:
                    continue

            if event_date and start.date() <= event_date.date() <= end.date():
                is_utmb = "utmb" in title.lower()
                events.append(SportEvent(
                    sport="Trail",
                    league="UTMB World Series" if is_utmb else "Trail",
                    league_emoji="🏔️",
                    date=event_date,
                    title=title,
                    status="upcoming",
                    is_must_watch=is_utmb,
                ))
    except Exception as e:
        logger.warning("UTMB scraping failed: %s", e)

    return events


def fetch_athletics(config: dict, date_range: str) -> list[SportEvent]:
    """Fetch athletics events via ESPN."""
    events: list[SportEvent] = []
    try:
        from src.fetch.espn import espn
        articles = espn.news("olympics", "athletics", limit=5)
        for a in articles:
            title = a.get("headline", "")
            if title:
                events.append(SportEvent(
                    sport="Athlétisme",
                    league="World Athletics",
                    league_emoji="🏃",
                    date=datetime.now(tz=timezone.utc),
                    title=title,
                    status="upcoming",
                ))
    except Exception as e:
        logger.warning("Athletics fetch failed: %s", e)
    return events


def fetch_swimming(config: dict, date_range: str) -> list[SportEvent]:
    """Fetch swimming events from World Aquatics."""
    events: list[SportEvent] = []

    try:
        parts = date_range.split("-")
        start = datetime.strptime(parts[0], "%Y%m%d")
        end = datetime.strptime(parts[1], "%Y%m%d") if len(parts) > 1 else start + timedelta(days=7)
    except (ValueError, IndexError):
        start = datetime.now()
        end = start + timedelta(days=7)

    try:
        r = requests.get(
            WORLD_AQUATICS_URL,
            headers={"User-Agent": "SportWeekly/1.0"},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        for item in soup.select(".competition-item, .event-card, article"):
            title_el = item.select_one("h2, h3, .title, .competition-name")
            date_el = item.select_one(".date, time")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            if any(kw in title.lower() for kw in ["world", "championship", "mondial", "olympic"]):
                events.append(SportEvent(
                    sport="Natation",
                    league="World Aquatics",
                    league_emoji="🏊",
                    date=datetime.now(tz=timezone.utc),
                    title=title,
                    status="upcoming",
                    is_must_watch=True,
                ))
    except Exception as e:
        logger.warning("World Aquatics scraping failed: %s", e)

    return events


def fetch_endurance_news(config: dict) -> list[dict]:
    try:
        from src.fetch.espn import espn
        articles = espn.news("olympics", "athletics", limit=3)
        return [{"title": a.get("headline", ""), "url": a.get("links", {}).get("web", {}).get("href", "")} for a in articles]
    except Exception:
        return []
