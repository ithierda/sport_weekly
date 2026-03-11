"""Cycling fetcher — CyclingNews RSS for race stages & news."""

import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import feedparser

from src.fetch.espn import SportEvent

logger = logging.getLogger(__name__)

TIMEOUT = 30
PARIS_TZ = ZoneInfo("Europe/Paris")

CYCLING_NEWS_RSS = "https://www.cyclingnews.com/rss/"

# Keywords to detect stage/race results in RSS
RACE_KEYWORDS = [
    "stage", "étape", "wins", "victory", "sprint", "time trial",
    "gc", "general classification", "overall", "crash", "abandon",
    "paris-nice", "tirreno", "milan-san remo", "roubaix", "flandres",
    "tour de france", "giro", "vuelta", "liège", "lombardia",
    "strade bianche", "primavera",
]

MONUMENTS = ["Milan-San Remo", "Tour des Flandres", "Paris-Roubaix", "Liège-Bastogne-Liège", "Il Lombardia"]
GRAND_TOURS = ["Tour de France", "Giro d'Italia", "Vuelta a España"]


def _extract_race_name(title: str) -> str:
    """Try to extract the race name from a CyclingNews title."""
    # Common patterns: "Paris-Nice: ..." or "Tirreno-Adriatico: ..."
    if ":" in title:
        prefix = title.split(":")[0].strip()
        # Check if prefix looks like a race name (not too long, not a quote)
        if len(prefix) < 40 and not prefix.startswith("'") and not prefix.startswith('"'):
            return prefix
    return ""


def fetch_cycling(config: dict, date_range: str) -> list[SportEvent]:
    """Fetch cycling events from CyclingNews RSS."""
    events: list[SportEvent] = []

    try:
        feed = feedparser.parse(CYCLING_NEWS_RSS)
        seen_titles: set[str] = set()
        riders = [r.lower() for r in config.get("riders", [])]

        for entry in feed.entries[:20]:
            title = entry.get("title", "")
            title_lower = title.lower()

            # Filter for race-related news
            if not any(kw in title_lower for kw in RACE_KEYWORDS):
                continue

            race_name = _extract_race_name(title)
            if not race_name:
                # Try to detect race from content
                for gt in GRAND_TOURS + MONUMENTS + ["Paris-Nice", "Tirreno-Adriatico", "Strade Bianche"]:
                    if gt.lower() in title_lower:
                        race_name = gt
                        break
                if not race_name:
                    race_name = "Cyclisme"

            # Avoid duplicates on same race
            dedup_key = f"{race_name}"
            if dedup_key in seen_titles and len(events) > 3:
                continue
            seen_titles.add(dedup_key)

            # Parse published date
            pub = entry.get("published_parsed")
            if pub:
                dt = datetime(*pub[:6], tzinfo=timezone.utc).astimezone(PARIS_TZ)
            else:
                dt = datetime.now(tz=PARIS_TZ)

            is_monument = any(m.lower() in race_name.lower() for m in MONUMENTS)
            is_grand_tour = any(gt.lower() in race_name.lower() for gt in GRAND_TOURS)
            rider_mentioned = any(r in title_lower for r in riders)

            events.append(SportEvent(
                sport="Cyclisme",
                league=race_name,
                league_emoji="🚴",
                date=dt,
                title=title,
                status="upcoming",
                is_must_watch=is_monument or is_grand_tour or rider_mentioned,
                details="Monument" if is_monument else ("Grand Tour" if is_grand_tour else ""),
            ))

    except Exception as e:
        logger.warning("CyclingNews RSS failed: %s", e)

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
            pub = entry.get("published", "")
            priority = any(r in title.lower() for r in riders)
            articles.append({"title": title, "url": link, "published": pub, "priority": priority})
        return sorted(articles, key=lambda x: x.get("priority", False), reverse=True)[:5]
    except Exception as e:
        logger.warning("CyclingNews RSS failed: %s", e)
        return []
