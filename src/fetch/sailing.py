"""Sailing fetcher — SailGP & Vendée Globe."""

import logging
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

from src.fetch.espn import SportEvent

logger = logging.getLogger(__name__)

TIMEOUT = 30

SAILGP_CALENDAR_URL = "https://sailgp.com/races/"
VENDEE_GLOBE_URL = "https://www.vendeeglobe.org/en"


def fetch_sailing(config: dict, date_range: str) -> list[SportEvent]:
    """Fetch sailing events — SailGP & Vendée Globe."""
    events: list[SportEvent] = []
    event_types = config.get("events", [])

    try:
        parts = date_range.split("-")
        start = datetime.strptime(parts[0], "%Y%m%d")
        end = datetime.strptime(parts[1], "%Y%m%d") if len(parts) > 1 else start + timedelta(days=7)
    except (ValueError, IndexError):
        start = datetime.now()
        end = start + timedelta(days=7)

    if "sailgp" in event_types:
        events.extend(_fetch_sailgp(start, end))

    if "vendee_globe" in event_types:
        events.extend(_fetch_vendee_globe(start, end))

    return events


def _fetch_sailgp(start: datetime, end: datetime) -> list[SportEvent]:
    """Scrape SailGP race calendar."""
    events = []
    try:
        r = requests.get(
            SAILGP_CALENDAR_URL,
            headers={"User-Agent": "SportWeekly/1.0"},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        for item in soup.select(".race-card, .event-card, article, .schedule-item"):
            title_el = item.select_one("h2, h3, .race-title, .title")
            date_el = item.select_one(".date, time, .race-date")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            date_str = date_el.get("datetime", date_el.get_text(strip=True)) if date_el else ""

            event_date = None
            for fmt in ["%Y-%m-%d", "%d %B %Y", "%B %d, %Y", "%d %b %Y"]:
                try:
                    event_date = datetime.strptime(date_str.strip(), fmt).replace(tzinfo=timezone.utc)
                    break
                except ValueError:
                    continue

            if event_date and start.date() <= event_date.date() <= end.date():
                events.append(SportEvent(
                    sport="Voile",
                    league="SailGP",
                    league_emoji="⛵",
                    date=event_date,
                    title=f"SailGP — {title}",
                    status="upcoming",
                    is_must_watch=True,
                ))
    except Exception as e:
        logger.warning("SailGP scraping failed: %s", e)

    return events


def _fetch_vendee_globe(start: datetime, end: datetime) -> list[SportEvent]:
    """Check Vendée Globe news/status (next edition ~2028)."""
    events = []
    try:
        r = requests.get(
            VENDEE_GLOBE_URL,
            headers={"User-Agent": "SportWeekly/1.0"},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Look for upcoming events or news
        for item in soup.select("article, .news-item, .actu-item"):
            title_el = item.select_one("h2, h3, .title")
            if title_el:
                title = title_el.get_text(strip=True)
                if any(kw in title.lower() for kw in ["race", "start", "départ", "arrivée", "classement"]):
                    events.append(SportEvent(
                        sport="Voile",
                        league="Vendée Globe",
                        league_emoji="⛵",
                        date=datetime.now(tz=timezone.utc),
                        title=f"Vendée Globe — {title}",
                        status="upcoming",
                        is_must_watch=True,
                    ))
                    break
    except Exception as e:
        logger.warning("Vendée Globe scraping failed: %s", e)

    return events


def fetch_sailing_news(config: dict) -> list[dict]:
    return []
