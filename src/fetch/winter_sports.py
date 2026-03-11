"""Biathlon & Ski Alpine fetcher — IBU & FIS scraping."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import requests
import feedparser
from bs4 import BeautifulSoup

from src.fetch.espn import SportEvent

logger = logging.getLogger(__name__)

TIMEOUT = 30

# IBU (International Biathlon Union)
IBU_CALENDAR_URL = "https://www.biathlonworld.com/calendar"
IBU_RSS = "https://www.biathlonworld.com/rss"

# FIS (International Ski Federation)
FIS_CALENDAR_URL = "https://www.fis-ski.com/DB/alpine-skiing/calendar-results.html"


def _parse_date_safe(text: str, year: int) -> datetime | None:
    for fmt in ["%d %b %Y", "%d.%m.%Y", "%Y-%m-%d", "%d %B %Y"]:
        try:
            return datetime.strptime(text.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def fetch_biathlon(config: dict, date_range: str) -> list[SportEvent]:
    """Fetch biathlon events from IBU calendar."""
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
            IBU_CALENDAR_URL,
            headers={"User-Agent": "SportWeekly/1.0"},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        for item in soup.select(".calendar-event, .event-item, article"):
            title_el = item.select_one("h3, h4, .event-title, .title")
            date_el = item.select_one(".date, time, .event-date")
            if not title_el or not date_el:
                continue

            title = title_el.get_text(strip=True)
            date_str = date_el.get("datetime", date_el.get_text(strip=True))
            event_date = _parse_date_safe(date_str, start.year)

            if event_date and start.date() <= event_date.date() <= end.date():
                is_wc = "world cup" in title.lower() or "coupe du monde" in title.lower()
                events.append(SportEvent(
                    sport="Biathlon",
                    league="Coupe du Monde IBU" if is_wc else "IBU Cup",
                    league_emoji="🎿",
                    date=event_date,
                    title=title,
                    status="upcoming",
                    is_must_watch=is_wc,
                ))
    except Exception as e:
        logger.warning("IBU calendar scraping failed: %s", e)

    # Fallback: RSS feed
    if not events:
        try:
            feed = feedparser.parse(IBU_RSS)
            for entry in feed.entries[:5]:
                title = entry.get("title", "")
                if any(kw in title.lower() for kw in ["race", "sprint", "pursuit", "mass start", "relay", "individual"]):
                    events.append(SportEvent(
                        sport="Biathlon",
                        league="IBU",
                        league_emoji="🎿",
                        date=datetime.now(tz=timezone.utc),
                        title=title,
                        status="upcoming",
                    ))
        except Exception as e:
            logger.warning("IBU RSS failed: %s", e)

    return events


def fetch_ski_alpine(config: dict, date_range: str) -> list[SportEvent]:
    """Fetch ski alpine events from FIS calendar."""
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
            FIS_CALENDAR_URL,
            params={"seasoncode": f"{'%d' % start.year}", "categorycode": "WC"},
            headers={"User-Agent": "SportWeekly/1.0"},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        for row in soup.select("div.table-row, tr.table__row"):
            date_el = row.select_one(".g-sm-3, .date, td:first-child")
            event_el = row.select_one(".g-sm-5, .event, td:nth-child(3)")
            place_el = row.select_one(".g-sm-4, .place, td:nth-child(2)")

            if not date_el or not event_el:
                continue

            date_text = date_el.get_text(strip=True)
            event_name = event_el.get_text(strip=True)
            place = place_el.get_text(strip=True) if place_el else ""

            event_date = _parse_date_safe(date_text, start.year)
            if event_date and start.date() <= event_date.date() <= end.date():
                title = f"{event_name} — {place}" if place else event_name
                events.append(SportEvent(
                    sport="Ski Alpin",
                    league="Coupe du Monde FIS",
                    league_emoji="⛷️",
                    date=event_date,
                    title=title,
                    status="upcoming",
                    venue=place,
                ))
    except Exception as e:
        logger.warning("FIS calendar scraping failed: %s", e)

    return events


def fetch_winter_sports_news(config: dict) -> list[dict]:
    try:
        feed = feedparser.parse(IBU_RSS)
        return [{"title": e.get("title", ""), "url": e.get("link", "")} for e in feed.entries[:3]]
    except Exception:
        return []
