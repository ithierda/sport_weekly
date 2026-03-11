"""Main orchestrator — fetches all sports, generates AI summary, renders & sends newsletter."""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.config import Config
from src.fetch.espn import SportEvent
from src.fetch.football import fetch_football, fetch_football_news
from src.fetch.rugby import fetch_rugby, fetch_rugby_news
from src.fetch.nba import fetch_nba, fetch_nba_news
from src.fetch.tennis import fetch_tennis, fetch_tennis_news
from src.fetch.motorsport import fetch_f1, fetch_motogp, fetch_motorsport_news
from src.fetch.cycling import fetch_cycling, fetch_cycling_news
from src.fetch.winter_sports import fetch_biathlon, fetch_ski_alpine, fetch_winter_sports_news
from src.fetch.sailing import fetch_sailing, fetch_sailing_news
from src.fetch.endurance import fetch_trail, fetch_athletics, fetch_swimming, fetch_endurance_news
from src.fetch.olympics import fetch_olympics, fetch_olympics_news
from src.model.hf_client import generate, build_weekly_prompt
from src.send.render import render_newsletter
from src.send.mailer import send_mail

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

cfg = Config()

# Sport fetcher registry: maps config key → (fetcher_fn, news_fn)
SPORT_FETCHERS = {
    "football": (fetch_football, fetch_football_news),
    "rugby": (fetch_rugby, fetch_rugby_news),
    "nba": (fetch_nba, fetch_nba_news),
    "tennis": (fetch_tennis, fetch_tennis_news),
    "f1": (lambda c, dr: fetch_f1(c, dr), fetch_motorsport_news),
    "motogp": (lambda c, dr: fetch_motogp(c, dr), lambda c: []),
    "cycling": (fetch_cycling, fetch_cycling_news),
    "biathlon": (lambda c, dr: fetch_biathlon(c, dr), fetch_winter_sports_news),
    "ski_alpine": (lambda c, dr: fetch_ski_alpine(c, dr), lambda c: []),
    "sailing": (fetch_sailing, fetch_sailing_news),
    "trail": (lambda c, dr: fetch_trail(c, dr), fetch_endurance_news),
    "athletics": (lambda c, dr: fetch_athletics(c, dr), lambda c: []),
    "swimming": (lambda c, dr: fetch_swimming(c, dr), lambda c: []),
    "olympics": (fetch_olympics, fetch_olympics_news),
}


def load_user_configs() -> list[dict]:
    """Load all user configuration files from config/users/."""
    config_dir = Path(__file__).parent.parent / "config" / "users"
    configs = []
    if not config_dir.exists():
        logger.error("Config directory not found: %s", config_dir)
        return configs

    for f in sorted(config_dir.glob("*.json")):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                data["_file"] = f.name
                configs.append(data)
                logger.info("Loaded config: %s (%s)", data.get("name", "?"), f.name)
        except Exception as e:
            logger.error("Failed to load %s: %s", f.name, e)

    return configs


def _format_date_range(start: datetime, end: datetime) -> str:
    """Format date range for ESPN API: YYYYMMDD-YYYYMMDD."""
    return f"{start.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}"


def _events_to_text(events: list[SportEvent]) -> str:
    """Convert events to text for AI prompt."""
    if not events:
        return "Aucun événement trouvé."

    lines = []
    current_day = ""
    for ev in sorted(events, key=lambda e: e.date):
        day = ev.date.strftime("%A %d/%m")
        if day != current_day:
            current_day = day
            lines.append(f"\n--- {day} ---")

        time_str = ev.date.strftime("%H:%M") if ev.date.hour > 0 else ""
        if ev.home_team and ev.away_team:
            match_str = f"{ev.away_team} @ {ev.home_team}"
            if ev.home_score is not None:
                match_str += f" ({ev.home_score}-{ev.away_score})"
        else:
            match_str = ev.title

        line = f"  [{ev.league_emoji} {ev.league}] {match_str}"
        if time_str:
            line += f" — {time_str}"
        if ev.round_info:
            line += f" ({ev.round_info})"
        lines.append(line)

    return "\n".join(lines)


def _must_watch_to_text(events: list[SportEvent]) -> str:
    """Convert must-watch events to text for AI prompt."""
    must = [e for e in events if e.is_must_watch and e.status == "upcoming"]
    if not must:
        return "Pas de gros événements identifiés cette semaine."

    lines = []
    for i, ev in enumerate(must[:7], 1):
        day = ev.date.strftime("%A %d/%m")
        if ev.home_team and ev.away_team:
            title = f"{ev.away_team} vs {ev.home_team}"
        else:
            title = ev.title
        lines.append(f"{i}. [{ev.sport}] {title} — {day}")
        if ev.details:
            lines.append(f"   {ev.details}")
    return "\n".join(lines)


def _news_to_text(news: list[dict]) -> str:
    """Convert news to text for AI prompt."""
    if not news:
        return "Pas d'actualités disponibles."
    return "\n".join(f"• {n.get('title', '')}" for n in news[:15])


def run_for_user(user_config: dict, dry_run: bool = False):
    """Run the full pipeline for one user."""
    name = user_config.get("name", "Ami")
    email = user_config.get("email", "")
    sports = user_config.get("sports", {})

    logger.info("=== Processing user: %s (%s) ===", name, email)

    # Determine week range (this Monday → next Sunday)
    now = datetime.now(tz=timezone.utc)
    monday = now - timedelta(days=now.weekday())  # Start of current week
    sunday = monday + timedelta(days=6)
    date_range = _format_date_range(monday, sunday)

    logger.info("Week range: %s to %s", monday.strftime("%d/%m"), sunday.strftime("%d/%m"))

    # Fetch all events & news
    all_events: list[SportEvent] = []
    all_news: list[dict] = []

    for sport_key, sport_config in sports.items():
        if sport_key not in SPORT_FETCHERS:
            logger.warning("Unknown sport: %s", sport_key)
            continue

        # Check if sport is enabled (simple bool or dict)
        if isinstance(sport_config, dict) and not sport_config.get("follow", True) and not sport_config.get("follow_league", True):
            if not sport_config.get("leagues") and not sport_config.get("events") and not sport_config.get("players"):
                continue

        fetch_fn, news_fn = SPORT_FETCHERS[sport_key]

        try:
            logger.info("Fetching %s...", sport_key)
            events = fetch_fn(sport_config if isinstance(sport_config, dict) else {}, date_range)
            all_events.extend(events)
            logger.info("  → %d events", len(events))
        except Exception as e:
            logger.error("Failed to fetch %s: %s", sport_key, e)

        try:
            news = news_fn(sport_config if isinstance(sport_config, dict) else {})
            all_news.extend(news)
        except Exception as e:
            logger.warning("Failed to fetch %s news: %s", sport_key, e)

    logger.info("Total: %d events, %d news items", len(all_events), len(all_news))

    # Generate AI summary
    ai_summary = ""
    if all_events or all_news:
        try:
            events_text = _events_to_text(all_events)
            must_watch_text = _must_watch_to_text(all_events)
            news_text = _news_to_text(all_news)
            prompt = build_weekly_prompt(events_text, news_text, must_watch_text)
            ai_summary = generate(prompt)
            if ai_summary:
                logger.info("AI summary generated (%d chars)", len(ai_summary))
        except Exception as e:
            logger.error("AI generation failed: %s", e)

    # Render HTML
    html = render_newsletter(
        user_name=name,
        week_start=monday,
        week_end=sunday,
        events=all_events,
        ai_summary=ai_summary,
        news=all_news,
    )

    # Save output
    out_dir = Path(__file__).parent.parent / "out"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"newsletter_{name.lower().replace(' ', '_')}_{monday.strftime('%Y%m%d')}.html"
    out_file.write_text(html, encoding="utf-8")
    logger.info("Newsletter saved to %s", out_file)

    # Send email
    if not dry_run and email:
        week_str = f"{monday.strftime('%d/%m')} au {sunday.strftime('%d/%m/%Y')}"
        subject = f"🏆 Sport Weekly — Semaine du {week_str}"
        send_mail(html, subject, [email])
    elif dry_run:
        logger.info("DRY RUN — email not sent")
    else:
        logger.warning("No email configured for %s", name)


def run(dry_run: bool = False):
    """Run the newsletter for all configured users."""
    users = load_user_configs()
    if not users:
        logger.error("No user configs found in config/users/")
        return

    for user in users:
        try:
            run_for_user(user, dry_run=dry_run)
        except Exception as e:
            logger.error("Failed for user %s: %s", user.get("name", "?"), e, exc_info=True)

    logger.info("Done — %d users processed", len(users))
