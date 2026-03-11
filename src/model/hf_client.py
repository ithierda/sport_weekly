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
    """Build the prompt for weekly newsletter AI commentary."""
    return f"""TU ES UN JOURNALISTE SPORTIF avec le style Trashtalk / la verve de L'Équipe.
Tu rédiges le résumé hebdomadaire d'une newsletter sportive multi-sports en FRANÇAIS.

RÈGLES STRICTES :
1. Écris en FRANÇAIS, avec un style percutant et divertissant.
2. Utilise UNIQUEMENT les données fournies ci-dessous. NE FABRIQUE AUCUNE information.
3. Pas d'emojis, pas de titres, pas de formatage, juste des paragraphes fluides.
4. Commence directement dans le vif du sujet.
5. Mets en avant les 5 événements à ne pas rater de la semaine avec du HYPE.
6. Fais des transitions naturelles entre les sports.
7. Sois insolent mais jamais méchant, factuel mais jamais ennuyeux.
8. Si tu ne disposes pas d'assez de données sur un sport, mentionne-le brièvement ou ignore-le. 
   Pas de données = pas d'invention.
9. Intègre les actualités et tendances du moment.
10. Termine par une phrase punch pour donner envie de suivre la semaine.
11. Longueur : 800-1200 mots.

═══ TOP 5 À NE PAS RATER CETTE SEMAINE ═══
{must_watch}

═══ PROGRAMME DE LA SEMAINE ═══
{events_summary}

═══ ACTUALITÉS ═══
{news_summary}

RÉDIGE MAINTENANT TON RÉSUMÉ :"""
