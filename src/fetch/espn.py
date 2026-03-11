"""Generic ESPN API client for fetching sports data."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field

import requests

logger = logging.getLogger(__name__)

TIMEOUT = 30


@dataclass
class SportEvent:
    sport: str
    league: str
    league_emoji: str
    date: datetime
    title: str
    status: str  # "upcoming" | "completed" | "in_progress"
    home_team: str = ""
    away_team: str = ""
    home_score: int | None = None
    away_score: int | None = None
    round_info: str = ""
    venue: str = ""
    is_must_watch: bool = False
    details: str = ""


class ESPNClient:
    """Fetches data from ESPN's public API."""

    BASE = "https://site.api.espn.com/apis/site/v2/sports"

    def scoreboard(self, sport: str, league: str, dates: str | None = None) -> dict:
        url = f"{self.BASE}/{sport}/{league}/scoreboard"
        params = {}
        if dates:
            params["dates"] = dates
        try:
            r = requests.get(url, params=params, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("ESPN scoreboard error (%s/%s): %s", sport, league, e)
            return {}

    def news(self, sport: str, league: str, limit: int = 10) -> list[dict]:
        url = f"{self.BASE}/{sport}/{league}/news"
        try:
            r = requests.get(url, params={"limit": limit}, timeout=TIMEOUT)
            r.raise_for_status()
            data = r.json()
            return data.get("articles", [])
        except Exception as e:
            logger.warning("ESPN news error (%s/%s): %s", sport, league, e)
            return []

    def parse_events(
        self,
        data: dict,
        sport_label: str,
        league_label: str,
        emoji: str,
        team_filter: list[str] | None = None,
        player_filter: list[str] | None = None,
    ) -> list[SportEvent]:
        """Parse ESPN scoreboard JSON into SportEvent list."""
        events: list[SportEvent] = []
        for ev in data.get("events", []):
            try:
                dt = datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue

            name = ev.get("name", ev.get("shortName", ""))
            status_obj = ev.get("status", {}).get("type", {})
            completed = status_obj.get("completed", False)
            state = status_obj.get("state", "pre")

            if completed:
                status = "completed"
            elif state == "in":
                status = "in_progress"
            else:
                status = "upcoming"

            comps = ev.get("competitions", [{}])
            comp = comps[0] if comps else {}
            competitors = comp.get("competitors", [])

            home_team = away_team = ""
            home_score = away_score = None
            for c in competitors:
                team_name = c.get("team", {}).get("displayName", c.get("team", {}).get("name", ""))
                score_str = c.get("score", "")
                ha = c.get("homeAway", "")
                score_val = int(score_str) if score_str and score_str.isdigit() else None
                if ha == "home":
                    home_team = team_name
                    home_score = score_val
                else:
                    away_team = team_name
                    away_score = score_val

            # Team filter
            if team_filter:
                matched = False
                for tf in team_filter:
                    tf_low = tf.lower()
                    if tf_low in home_team.lower() or tf_low in away_team.lower() or tf_low in name.lower():
                        matched = True
                        break
                if not matched:
                    continue

            venue = comp.get("venue", {}).get("fullName", "")
            round_info = comp.get("notes", [{}])[0].get("headline", "") if comp.get("notes") else ""

            # Determine must-watch based on round (knockout, final, semi, etc.)
            must_keywords = ["final", "semi", "quarter", "knockout", "demi", "quart"]
            is_must = any(kw in round_info.lower() or kw in name.lower() for kw in must_keywords)

            events.append(SportEvent(
                sport=sport_label,
                league=league_label,
                league_emoji=emoji,
                date=dt,
                title=name,
                status=status,
                home_team=home_team,
                away_team=away_team,
                home_score=home_score,
                away_score=away_score,
                round_info=round_info,
                venue=venue,
                is_must_watch=is_must,
            ))
        return events


# Singleton
espn = ESPNClient()
