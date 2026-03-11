"""Cycling fetcher — World Tour, Monuments, Classics via ProCyclingStats & RSS."""

import logging
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

import requests
import feedparser
from bs4 import BeautifulSoup

from src.fetch.espn import SportEvent

logger = logging.getLogger(__name__)

TIMEOUT = 30

# Major races calendar — manually maintained since cycling calendars are stable
MONUMENTS = ["Milan-San Remo", "Tour des Flandres", "Paris-Roubaix", "Liège-Bastogne-Liège", "Il Lombardia"]
GRAND_TOURS = ["Tour de France", "Giro d'Italia", "Vuelta a España"]

PCS_RACE_CALENDAR_URL = "https://www.procyclingstats.com/races.php"
FIRSTCYCLING_URL = "https://firstcycling.com/race.php"
CYCLING_NEWS_RSS = "https://www.cyclingnews.com/rss/"


def fetch_cycling(config: dict, date_range: str) -> list[SportEvent]:
    """Fetch cycling events from ProCyclingStats race calendar."""
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
            PCS_RACE_CALENDAR_URL,
            params={"year": start.year, "circuit": 1},  # circuit=1 → World Tour
            headers={"User-Agent": "SportWeekly/1.0"},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # PCS lists races in table rows
        for row in soup.select("table.basic tbody tr"):
            cols = row.find_all("td")
            if len(cols) < 4:
                continue
            date_text = cols[0].get_text(strip=True)
            race_name = cols[2].get_text(strip=True)

            try:
                race_date = datetime.strptime(f"{date_text}.{start.year}", "%d.%m.%Y")
            except ValueError:
                continue

            if start.date() <= race_date.date() <= end.date():
                is_monument = any(m.lower() in race_name.lower() for m in MONUMENTS)
                is_grand_tour = any(gt.lower() in race_name.lower() for gt in GRAND_TOURS)
                events.append(SportEvent(
                    sport="Cyclisme",
                    league="World Tour",
                    league_emoji="🚴",
                    date=race_date.replace(tzinfo=timezone.utc),
                    title=race_name,
                    status="upcoming",
                    is_must_watch=is_monument or is_grand_tour,
                    details="Monument" if is_monument else ("Grand Tour" if is_grand_tour else ""),
                ))
    except Exception as e:
        logger.warning("ProCyclingStats scraping failed: %s", e)

    # Fallback: ESPN cycling news as events
    if not events:
        from src.fetch.espn import espn
        articles = espn.news("racing", "cycling", limit=5)
        for a in articles:
            title = a.get("headline", "")
            if title:
                events.append(SportEvent(
                    sport="Cyclisme",
                    league="World Tour",
                    league_emoji="🚴",
                    date=start.replace(tzinfo=timezone.utc),
                    title=title,
                    status="upcoming",
                ))

    return events


def fetch_cycling_news(config: dict) -> list[dict]:
    """Fetch cycling news from CyclingNews RSS."""
    try:
        feed = feedparser.parse(CYCLING_NEWS_RSS)
        riders = [r.lower() for r in config.get("riders", [])]
        articles = []
        for entry in feed.entries[:10]:
            title = entry.get("title", "")
            link = entry.get("link", "")
            # Prioritize articles mentioning followed riders
            priority = any(r in title.lower() for r in riders)
            articles.append({"title": title, "url": link, "priority": priority})
        return sorted(articles, key=lambda x: x.get("priority", False), reverse=True)[:5]
    except Exception as e:
        logger.warning("CyclingNews RSS failed: %s", e)
        return []
