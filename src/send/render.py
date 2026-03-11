"""HTML email renderer for Sport Weekly newsletter."""

import logging
from datetime import datetime
from collections import defaultdict

from premailer import transform

from src.fetch.espn import SportEvent

logger = logging.getLogger(__name__)

# French day names
JOURS = {
    0: "Lundi", 1: "Mardi", 2: "Mercredi", 3: "Jeudi",
    4: "Vendredi", 5: "Samedi", 6: "Dimanche",
}
MOIS = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril", 5: "mai", 6: "juin",
    7: "juillet", 8: "août", 9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre",
}

# Sport colors for visual distinction
SPORT_COLORS = {
    "Football": "#2E7D32",
    "Rugby": "#1565C0",
    "NBA": "#E65100",
    "Tennis": "#6A1B9A",
    "F1": "#C62828",
    "MotoGP": "#AD1457",
    "Cyclisme": "#F9A825",
    "Biathlon": "#00695C",
    "Ski Alpin": "#0277BD",
    "Voile": "#0097A7",
    "Natation": "#1976D2",
    "Athlétisme": "#FF6F00",
    "Trail": "#33691E",
    "Jeux Olympiques": "#FFD600",
}


def _french_date(dt: datetime) -> str:
    """Format a datetime as 'Lundi 11 mars'."""
    jour = JOURS.get(dt.weekday(), "")
    mois = MOIS.get(dt.month, "")
    return f"{jour} {dt.day} {mois}"


def _sport_color(sport: str) -> str:
    return SPORT_COLORS.get(sport, "#667eea")


def _render_must_watch(events: list[SportEvent]) -> str:
    """Render the Top 5 must-watch section."""
    must = [e for e in events if e.is_must_watch and e.status == "upcoming"]
    # Deduplicate and pick top 5 based on variety of sports
    seen_sports: dict[str, int] = {}
    top5: list[SportEvent] = []
    # First pass: diversify sports
    for e in must:
        if len(top5) >= 5:
            break
        count = seen_sports.get(e.sport, 0)
        if count < 2:
            top5.append(e)
            seen_sports[e.sport] = count + 1

    if not top5:
        return ""

    html = """
        <div class="section">
            <h2>🔥 TOP 5 — À NE PAS RATER CETTE SEMAINE</h2>
            <div class="top5-list">"""

    for i, ev in enumerate(top5, 1):
        color = _sport_color(ev.sport)
        date_str = _french_date(ev.date)
        html += f"""
                <div class="top5-item" style="display:flex; align-items:center; gap:12px; padding:12px; margin-bottom:8px; background:#f8f9ff; border-left:4px solid {color}; border-radius:4px;">
                    <div style="font-size:24px; font-weight:800; color:{color}; min-width:35px; text-align:center;">{i}</div>
                    <div>
                        <div style="font-weight:700; font-size:15px; color:#1a1a1a;">{ev.league_emoji} {ev.title}</div>
                        <div style="font-size:12px; color:#666; margin-top:2px;">{ev.league} — {date_str}</div>
                        {f'<div style="font-size:11px; color:{color}; margin-top:2px;">{ev.details}</div>' if ev.details else ''}
                    </div>
                </div>"""

    html += """
            </div>
        </div>"""
    return html


def _render_day_events(day_label: str, events: list[SportEvent]) -> str:
    """Render events for a single day, grouped by sport."""
    by_sport: dict[str, list[SportEvent]] = defaultdict(list)
    for e in events:
        key = f"{e.sport} — {e.league}"
        by_sport[key].append(e)

    html = f"""
        <div class="day-section" style="margin-bottom:20px;">
            <h3 style="font-size:16px; color:#1a1a1a; background:linear-gradient(90deg, #667eea22, transparent); padding:8px 12px; border-radius:4px; margin:0 0 10px 0;">
                📅 {day_label}
            </h3>"""

    for sport_key, sport_events in by_sport.items():
        sport_name = sport_events[0].sport
        color = _sport_color(sport_name)
        emoji = sport_events[0].league_emoji

        html += f"""
            <div style="margin:0 0 12px 8px;">
                <div style="font-size:13px; font-weight:700; color:{color}; margin-bottom:6px;">
                    {emoji} {sport_key}
                </div>"""

        for ev in sport_events:
            time_str = ev.date.strftime("%H:%M") if ev.date.hour > 0 else ""

            if ev.status == "completed" and ev.home_score is not None:
                score = f'<span style="font-weight:700; color:{color};">{ev.home_score} - {ev.away_score}</span>'
                match_line = f"{ev.home_team} {score} {ev.away_team}" if ev.home_team else ev.title
                badge = '<span style="display:inline-block; padding:1px 6px; border-radius:3px; font-size:10px; background:#e8f5e9; color:#2e7d32; font-weight:600;">TERMINÉ</span>'
            elif ev.status == "upcoming":
                match_line = f"{ev.away_team} @ {ev.home_team}" if ev.home_team and ev.away_team else ev.title
                badge = f'<span style="display:inline-block; padding:1px 6px; border-radius:3px; font-size:10px; background:#e3f2fd; color:#1565c0; font-weight:600;">{time_str}</span>' if time_str else ''
            else:
                match_line = ev.title
                badge = '<span style="display:inline-block; padding:1px 6px; border-radius:3px; font-size:10px; background:#fff3e0; color:#e65100; font-weight:600;">EN COURS</span>'

            must_star = ' <span style="color:#FFD600; font-size:12px;">★</span>' if ev.is_must_watch else ''

            html += f"""
                <div style="padding:6px 0 6px 12px; font-size:13px; border-bottom:1px solid #f0f0f0;">
                    {match_line}{must_star}
                    {badge}
                    {f'<div style="font-size:11px; color:#888; margin-top:1px;">{ev.round_info}</div>' if ev.round_info else ''}
                </div>"""

        html += """
            </div>"""

    html += """
        </div>"""
    return html


def render_newsletter(
    user_name: str,
    week_start: datetime,
    week_end: datetime,
    events: list[SportEvent],
    ai_summary: str,
    news: list[dict],
) -> str:
    """Render the full HTML newsletter."""

    week_label = f"Semaine du {week_start.day} au {week_end.day} {MOIS.get(week_end.month, '')} {week_end.year}"
    summary_html = ai_summary.replace("\n", "<br>") if ai_summary else ""

    # Group events by day
    by_day: dict[str, list[SportEvent]] = defaultdict(list)
    for e in events:
        day_key = e.date.strftime("%Y-%m-%d")
        by_day[day_key].append(e)

    # Sort days
    sorted_days = sorted(by_day.keys())

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            color: #1a1a1a;
            background: #f5f5f5;
            padding: 0;
            margin: 0;
            line-height: 1.6;
        }}
        .container {{
            max-width: 680px;
            margin: 0 auto;
            background: white;
        }}
        .header {{
            background: linear-gradient(135deg, #1a237e 0%, #c62828 50%, #1a237e 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 800;
            letter-spacing: 2px;
        }}
        .header p {{
            margin: 8px 0 0 0;
            font-size: 13px;
            opacity: 0.9;
        }}
        .content {{
            padding: 20px;
        }}
        .section {{
            margin-bottom: 25px;
        }}
        .section h2 {{
            font-size: 18px;
            color: #1a237e;
            border-bottom: 3px solid #c62828;
            padding-bottom: 10px;
            margin: 0 0 15px 0;
        }}
        .summary {{
            background: #fafafa;
            padding: 15px;
            border-left: 4px solid #c62828;
            border-radius: 4px;
            line-height: 1.7;
            font-size: 14px;
        }}
        .news-item {{
            padding: 10px 0;
            border-bottom: 1px solid #e0e0e0;
            font-size: 13px;
        }}
        .news-item:last-child {{ border-bottom: none; }}
        .news-item a {{
            color: #1a237e;
            text-decoration: none;
            font-weight: 600;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 15px 20px;
            text-align: center;
            font-size: 11px;
            color: #888;
            border-top: 1px solid #e0e0e0;
        }}
        @media (max-width: 600px) {{
            .header {{ padding: 20px 15px; }}
            .header h1 {{ font-size: 22px; }}
            .content {{ padding: 15px; }}
            .section h2 {{ font-size: 16px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏆 SPORT WEEKLY</h1>
            <p>Au menu cette semaine — {week_label}</p>
            <p style="font-size:11px; opacity:0.7;">Salut {user_name} !</p>
        </div>

        <div class="content">"""

    # AI Summary
    if summary_html:
        html += f"""
            <div class="section">
                <h2>🎙️ LE MOT DE LA RÉDAC'</h2>
                <div class="summary">
                    {summary_html}
                </div>
            </div>"""

    # Top 5 Must Watch
    html += _render_must_watch(events)

    # Events by day
    if sorted_days:
        html += """
            <div class="section">
                <h2>📋 PROGRAMME COMPLET DE LA SEMAINE</h2>"""

        for day_str in sorted_days:
            day_dt = datetime.strptime(day_str, "%Y-%m-%d")
            day_label = _french_date(day_dt)
            html += _render_day_events(day_label, by_day[day_str])

        html += """
            </div>"""
    else:
        html += """
            <div class="section">
                <h2>📋 PROGRAMME</h2>
                <p style="color:#888; font-size:14px;">Pas d'événements trouvés pour cette semaine. Les sources sont peut-être indisponibles.</p>
            </div>"""

    # News section
    if news:
        html += """
            <div class="section">
                <h2>📰 ACTU EN BREF</h2>"""
        for n in news[:10]:
            title = n.get("title", "")
            url = n.get("url", "")
            if url:
                html += f"""
                <div class="news-item">
                    <a href="{url}">{title}</a>
                </div>"""
            elif title:
                html += f"""
                <div class="news-item">{title}</div>"""
        html += """
            </div>"""

    # Footer
    html += f"""
        </div>

        <div class="footer">
            <p>Sport Weekly — Ta dose de sport de la semaine</p>
            <p style="margin-top:4px;">Généré automatiquement le {datetime.now().strftime("%d/%m/%Y à %H:%M")}</p>
            <p style="margin-top:4px;"><a href="https://github.com/your-username/sport-weekly" style="color:#667eea;">⚙️ Configurer mes préférences</a></p>
        </div>
    </div>
</body>
</html>"""

    # Inline CSS for email client compatibility
    try:
        html = transform(html)
    except Exception as e:
        logger.warning("Premailer CSS inlining failed: %s", e)

    return html
