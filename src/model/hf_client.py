"""HuggingFace Inference API client for AI-generated commentary."""

from __future__ import annotations

import logging

import requests

from src.config import Config

logger = logging.getLogger(__name__)
cfg = Config()


def generate(prompt: str, max_tokens: int | None = None) -> str:
    """Generate text using HuggingFace Inference API (OpenAI-compatible)."""
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty")

    token = cfg.HF_API_TOKEN
    if not token:
        logger.warning("HF_API_TOKEN not set — skipping AI summary")
        return ""

    try:
        logger.info("Generating AI summary with model %s", cfg.MODEL_ID)

        response = requests.post(
            "https://router.huggingface.co/v1/chat/completions",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "messages": [{"role": "user", "content": prompt}],
                "model": cfg.MODEL_ID,
                "max_tokens": max_tokens or cfg.MAX_TOKENS,
                "temperature": 0.8,
                "top_p": 0.95,
            },
            timeout=90,
        )
        response.raise_for_status()
        data = response.json()

        if "choices" in data and data["choices"]:
            text = data["choices"][0].get("message", {}).get("content", "")
            if text:
                return text.strip()

        logger.error("Unexpected HF API response: %s", data)
        return ""

    except Exception as e:
        logger.error("HF API error: %s", e)
        return ""


def build_weekly_prompt(events_summary: str, news_summary: str, must_watch: str) -> str:
    """Build the prompt for a punchy weekly highlight for the newsletter."""
    return f"""TU ES UN JOURNALISTE SPORTIF FRANÇAIS avec le style Trashtalk / la verve de L'Équipe.

Ta mission : écrire UNE COURTE ACTU qui donne du peps à la semaine sportive.
Cette actu doit mettre en avant UNE GROSSE CONFRONTATION du week-end.

RÈGLES STRICTES :
1. Écris en FRANÇAIS.
2. Utilise UNIQUEMENT les informations ci-dessous. N'invente rien.
3. Choisis UN événement majeur (match, duel, rivalité, finale, choc historique).
4. Ton style doit être punchy, rythmé et légèrement insolent.
5. Pas d'emojis, pas de titres, pas de formatage.
6. Longueur : 2 à 4 phrases maximum.
7. Mets du HYPE autour du duel ou de l'événement.
8. Si possible, ajoute un contexte sympa (rivalité, anniversaire, revanche, série en cours).
9. Termine par une phrase qui donne envie de regarder.

═══ TOP ÉVÉNEMENTS À SURVEILLER ═══
{must_watch}

═══ PROGRAMME DE LA SEMAINE ═══
{events_summary}

═══ ACTUALITÉS SPORTIVES ═══
{news_summary}

RÉDIGE L'ACTU PUNCHY MAINTENANT :"""
