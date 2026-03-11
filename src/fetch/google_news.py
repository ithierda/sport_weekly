"""Google News RSS aggregator — surfaces recent sport articles from L'Équipe, Eurosport, etc."""

from __future__ import annotations

import logging
import urllib.parse
from datetime import datetime, timezone

import feedparser

logger = logging.getLogger(__name__)

# Targeted French sport queries (Google News returns L'Équipe & Eurosport articles)
_QUERIES = [
    "résultats football ligue 1 champions league site:lequipe.fr OR site:eurosport.fr",
    "cyclisme étape résultat site:lequipe.fr OR site:eurosport.fr",
    "arthur fils tennis résultat site:lequipe.fr OR site:eurosport.fr",
    "rugby top 14 champions cup résultat site:lequipe.fr OR site:eurosport.fr",
    "formule 1 grand prix site:lequipe.fr OR site:eurosport.fr",
]

_GNEWS_BASE = "https://news.google.com/rss/search"


def _gnews_url(query: str) -> str:
    return f"{_GNEWS_BASE}?q={urllib.parse.quote(query)}&hl=fr&gl=FR&ceid=FR:fr"


def fetch_french_sport_news(user_sports: dict | None = None) -> list[dict]:
    """Fetch recent sport headlines from Google News (L'Équipe / Eurosport sources).

    Returns a list of dicts with keys: title, url, source, published.
    """
    queries = list(_QUERIES)

    # Add user-sport-specific queries if relevant
    if user_sports:
        if user_sports.get("nba") or user_sports.get("basketball"):
            queries.append("NBA basketball résultat site:lequipe.fr OR site:eurosport.fr")
        if user_sports.get("biathlon") or user_sports.get("ski_alpine"):
            queries.append("biathlon ski alpin coupe du monde site:lequipe.fr OR site:eurosport.fr")
        if user_sports.get("motogp"):
            queries.append("motoGP grand prix résultat site:lequipe.fr OR site:eurosport.fr")

    articles: list[dict] = []
    seen: set[str] = set()

    for q in queries:
        try:
            feed = feedparser.parse(_gnews_url(q))
            for entry in feed.entries[:4]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                if not title or title in seen:
                    continue
                # Strip source suffix (e.g., " - L'Équipe")
                clean_title = title.rsplit(" - ", 1)[0].strip() if " - " in title else title
                if clean_title in seen:
                    continue
                seen.add(title)
                seen.add(clean_title)

                pub = entry.get("published_parsed")
                if pub:
                    pub_str = datetime(*pub[:6], tzinfo=timezone.utc).isoformat()
                else:
                    pub_str = ""

                source = entry.get("source", {}).get("title", "")
                articles.append({
                    "title": clean_title,
                    "url": link,
                    "source": source,
                    "published": pub_str,
                })
        except Exception as e:
            logger.warning("Google News RSS failed for query '%s': %s", q[:50], e)

    return articles
