"""Biathlon & Ski Alpine fetcher — biathlonworld.com & FIS scraping."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from src.fetch.espn import SportEvent

logger = logging.getLogger(__name__)

TIMEOUT = 30
PARIS_TZ = ZoneInfo("Europe/Paris")

# IBU (International Biathlon Union)
IBU_CALENDAR_URL = "https://www.biathlonworld.com/calendar"

# FIS (International Ski Federation)
FIS_CALENDAR_URL = "https://www.fis-ski.com/DB/alpine-skiing/calendar-results.html"

# Discipline labels
BIATHLON_DISCIPLINES = {
    "SP": "Sprint",
    "PU": "Poursuite",
    "IN": "Individuel",
    "MS": "Mass Start",
    "RL": "Relais",
    "SR": "Relais",
}

FIS_DISCIPLINES = {
    "DH": "Descente",
    "SG": "Super-G",
    "GS": "Géant",
    "SL": "Slalom",
    "AC": "Combiné",
    "PGS": "Géant Parallèle",
}


def fetch_biathlon(config: dict, date_range: str) -> list[SportEvent]:
    """Fetch biathlon events from biathlonworld.com Next.js data."""
    events: list[SportEvent] = []

    try:
        parts = date_range.split("-")
        start = datetime.strptime(parts[0], "%Y%m%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(parts[1], "%Y%m%d").replace(tzinfo=timezone.utc) if len(parts) > 1 else start + timedelta(days=7)
    except (ValueError, IndexError):
        start = datetime.now(tz=timezone.utc)
        end = start + timedelta(days=7)

    try:
        r = requests.get(IBU_CALENDAR_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        next_data = soup.select_one("script#__NEXT_DATA__")
        if not next_data:
            logger.warning("No __NEXT_DATA__ found on biathlonworld.com")
            return events

        data = json.loads(next_data.get_text())
        props = data.get("props", {}).get("pageProps", {})

        # Get the selected event info for location
        selected = props.get("eventInitialState", {}).get("selectedEvent", {})
        event_location = selected.get("ShortDescription", selected.get("Organizer", ""))
        event_country = selected.get("NatLong", "")

        # Get individual competitions (races) with times
        competitions = props.get("competitionsInitialState", [])
        for comp in competitions:
            start_time_str = comp.get("StartTime", "")
            if not start_time_str:
                continue

            try:
                dt = datetime.fromisoformat(start_time_str.replace("Z", "+00:00")).astimezone(PARIS_TZ)
            except (ValueError, TypeError):
                continue

            if not (start.date() <= dt.date() <= end.date()):
                continue

            description = comp.get("ShortDescription", comp.get("Description", ""))
            discipline = comp.get("DisciplineId", "")
            cat = comp.get("catId", "")
            location = comp.get("Location", event_location)

            # Determine gender
            gender = ""
            if cat == "SM":
                gender = "Hommes"
            elif cat == "SW":
                gender = "Femmes"
            elif cat == "MX":
                gender = "Mixte"

            disc_label = BIATHLON_DISCIPLINES.get(discipline, discipline)
            title = f"{description} — {event_location}"

            status_text = comp.get("StatusText", "Scheduled")
            if status_text in ("Official", "Final"):
                status = "completed"
            else:
                status = "upcoming"

            events.append(SportEvent(
                sport="Biathlon",
                league="Coupe du Monde IBU",
                league_emoji="🎿",
                date=dt,
                title=title,
                status=status,
                venue=location,
                is_must_watch=True,
                round_info=f"{gender} — {disc_label}" if gender else disc_label,
            ))

    except Exception as e:
        logger.warning("IBU biathlonworld.com scraping failed: %s", e)

    return events


def _parse_fis_date_range(text: str) -> tuple[datetime | None, datetime | None]:
    """Parse FIS date ranges like '04-08 Mar 2026' or '25 Feb-01 Mar 2026'."""
    text = text.strip()

    # Pattern: "04-08 Mar 2026"
    m = re.match(r"(\d{1,2})-(\d{1,2})\s+(\w+)\s+(\d{4})", text)
    if m:
        day1, day2, month_str, year = m.groups()
        try:
            start = datetime.strptime(f"{day1} {month_str} {year}", "%d %b %Y").replace(tzinfo=timezone.utc)
            end = datetime.strptime(f"{day2} {month_str} {year}", "%d %b %Y").replace(tzinfo=timezone.utc)
            return start, end
        except ValueError:
            pass

    # Pattern: "25 Feb-01 Mar 2026"
    m2 = re.match(r"(\d{1,2})\s+(\w+)-(\d{1,2})\s+(\w+)\s+(\d{4})", text)
    if m2:
        day1, mon1, day2, mon2, year = m2.groups()
        try:
            start = datetime.strptime(f"{day1} {mon1} {year}", "%d %b %Y").replace(tzinfo=timezone.utc)
            end = datetime.strptime(f"{day2} {mon2} {year}", "%d %b %Y").replace(tzinfo=timezone.utc)
            return start, end
        except ValueError:
            pass

    return None, None


def _parse_fis_disciplines(text: str) -> list[str]:
    """Parse discipline text like '2xSG 4xDH' or '5xDH SG' into discipline codes."""
    disciplines = []
    for code in FIS_DISCIPLINES:
        if code in text.upper():
            disciplines.append(code)
    return disciplines


def fetch_ski_alpine(config: dict, date_range: str) -> list[SportEvent]:
    """Fetch ski alpine events from FIS calendar."""
    events: list[SportEvent] = []

    try:
        parts = date_range.split("-")
        start = datetime.strptime(parts[0], "%Y%m%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(parts[1], "%Y%m%d").replace(tzinfo=timezone.utc) if len(parts) > 1 else start + timedelta(days=7)
    except (ValueError, IndexError):
        start = datetime.now(tz=timezone.utc)
        end = start + timedelta(days=7)

    try:
        r = requests.get(
            FIS_CALENDAR_URL,
            params={"seasoncode": str(start.year), "categorycode": "WC"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        for row in soup.select(".table-row.reset-padding, .table-row"):
            cells = row.select("[class*='g-']")
            if len(cells) < 5:
                continue

            # Extract date, location, country, discipline from cells
            date_text = ""
            location = ""
            country = ""
            disc_text = ""
            gender = ""

            for cell in cells:
                classes = " ".join(cell.get("class", []))
                text = cell.get_text(strip=True)

                if "g-lg-4" in classes and not date_text:
                    # Date cell — check for date-like content
                    if re.search(r"\d{1,2}.*\d{4}", text):
                        date_text = text
                elif "g-lg-7" in classes and "hidden-sm-down" in classes and not location:
                    location = text
                elif "g-lg-2" in classes and len(text) == 3 and text.isupper():
                    country = text
                elif "g-lg-7" in classes and "justify-left" in classes and ("WC" in text or "DH" in text or "SG" in text or "SL" in text or "GS" in text):
                    disc_text = text
                elif "hidden-sm-down" in classes and "bold" in classes and text in ("M", "W"):
                    gender = "Hommes" if text == "M" else "Femmes"

            if not date_text or not location:
                continue

            event_start, event_end = _parse_fis_date_range(date_text)
            if not event_start or not event_end:
                continue

            # Check if this event overlaps with our date range
            if event_end.date() < start.date() or event_start.date() > end.date():
                continue

            disciplines = _parse_fis_disciplines(disc_text)
            if not disciplines:
                disciplines = ["AL"]  # Generic alpine

            for disc_code in disciplines:
                disc_label = FIS_DISCIPLINES.get(disc_code, disc_code)
                title = f"{disc_label} {gender} — {location}" if gender else f"{disc_label} — {location}"

                events.append(SportEvent(
                    sport="Ski Alpin",
                    league="Coupe du Monde FIS",
                    league_emoji="⛷️",
                    date=event_start,
                    title=title,
                    status="upcoming",
                    venue=f"{location} ({country})",
                    is_must_watch=True,
                    round_info=f"Coupe du Monde — {disc_label}",
                ))

    except Exception as e:
        logger.warning("FIS calendar scraping failed: %s", e)

    return events


def fetch_winter_sports_news(config: dict) -> list[dict]:
    """Fetch biathlon news from biathlonworld.com."""
    try:
        r = requests.get(IBU_CALENDAR_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        next_data = soup.select_one("script#__NEXT_DATA__")
        if not next_data:
            return []
        data = json.loads(next_data.get_text())
        selected = data.get("props", {}).get("pageProps", {}).get("eventInitialState", {}).get("selectedEvent", {})
        if selected:
            loc = selected.get("ShortDescription", "")
            return [{"title": f"Biathlon Coupe du Monde — {loc}", "url": "https://www.biathlonworld.com/calendar"}]
    except Exception:
        pass
    return []
