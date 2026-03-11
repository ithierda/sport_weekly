# 🏆 Sport Weekly

**Ta dose hebdomadaire de sport, directement dans ta boîte mail.** 

Sport Weekly est un bot qui t'envoie chaque lundi matin une newsletter personnalisée avec le programme sportif de la semaine à venir — matchs, courses, événements — triés par jour et par sport. Le tout agrémenté d'un résumé IA piquant à la Trashtalk.

## 🎯 Fonctionnalités

- **Multi-sports** : Football, Rugby, NBA, Tennis, F1, MotoGP, Cyclisme, Biathlon, Ski, Voile, Natation, Athlétisme, Trail, JO
- **Personnalisable** : choisis tes sports, équipes, joueurs favoris via un simple fichier JSON
- **Top 5 à ne pas rater** : les événements phares de la semaine mis en avant
- **Résumé IA** : commentaire style Trashtalk généré par IA (HuggingFace)
- **Email responsive** : design soigné, lisible sur mobile
- **Multi-utilisateurs** : chaque ami crée son fichier de config
- **GitHub Actions** : envoi automatique chaque lundi à 9h (heure de Paris)

## 🚀 Quick Start

### 1. Fork & Clone

```bash
git clone https://github.com/YOUR_USERNAME/sport-weekly.git
cd sport-weekly
pip install -r requirements.txt
```

### 2. Configure ton profil

Copie l'exemple et personnalise :

```bash
cp config/users/example.json config/users/ton_prenom.json
```

Édite `config/users/ton_prenom.json` :

```json
{
    "name": "Ton Prénom",
    "email": "ton.email@gmail.com",
    "sports": {
        "football": {
            "leagues": ["champions_league"],
            "teams": ["Paris Saint-Germain"]
        },
        "rugby": {
            "leagues": ["top14", "champions_cup", "sevens"],
            "teams": ["France"]
        },
        "nba": {
            "follow_league": true,
            "players": ["Victor Wembanyama"]
        },
        "tennis": {
            "events": ["grand_slam", "masters_1000"],
            "players": ["Arthur Fils"]
        },
        "f1": { "follow": true },
        "cycling": {
            "events": ["world_tour", "monuments"],
            "riders": ["Pogacar"]
        }
    }
}
```

### 3. Configure l'environnement

```bash
cp .env.example .env
```

Remplis le `.env` avec :
- **Gmail** : utilise un [mot de passe d'application](https://support.google.com/accounts/answer/185833)
- **HuggingFace** : crée un token sur [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

### 4. Test

```bash
python run.py test    # Dry run (pas d'email)
python run.py once    # Envoyer la newsletter
python run.py schedule  # Lancer le scheduler local
```

## 📋 Sports disponibles

| Clé config | Sport | Source |
|------------|-------|--------|
| `football` | ⚽ Champions League, Ligue 1 | ESPN API |
| `rugby` | 🏉 Top 14, Champions Cup, France, Sevens | ESPN API |
| `nba` | 🏀 NBA + suivi joueur | ESPN API |
| `tennis` | 🎾 Grand Chelems, Masters 1000, ATP | ESPN API |
| `f1` | 🏎️ Formule 1 | ESPN API |
| `motogp` | 🏍️ MotoGP | ESPN API |
| `cycling` | 🚴 World Tour, Monuments, Classiques | ProCyclingStats |
| `biathlon` | 🎿 Coupe du Monde IBU | IBU scraping |
| `ski_alpine` | ⛷️ Coupe du Monde FIS | FIS scraping |
| `sailing` | ⛵ SailGP, Vendée Globe | Site officiel |
| `swimming` | 🏊 World Aquatics | Site officiel |
| `athletics` | 🏃 Diamond League, Mondiaux | World Athletics |
| `trail` | 🏔️ UTMB, grandes courses | UTMB World |
| `olympics` | 🏅 Jeux Olympiques | Olympics.com |

## ⚙️ Config détaillée par sport

### Football
```json
"football": {
    "leagues": ["champions_league", "ligue_1"],
    "teams": ["Paris Saint-Germain", "Real Madrid"]
}
```

### Rugby
```json
"rugby": {
    "leagues": ["top14", "champions_cup", "test_matches", "six_nations", "sevens"],
    "teams": ["France", "Stade Français"]
}
```

### Tennis
```json
"tennis": {
    "events": ["grand_slam", "masters_1000"],
    "players": ["Arthur Fils", "Djokovic"]
}
```

### Cyclisme
```json
"cycling": {
    "events": ["world_tour", "monuments", "classics"],
    "riders": ["Paul Seixas", "Julian Alaphilippe"]
}
```

## 🔧 Déploiement GitHub Actions

### Secrets à configurer

Dans ton repo GitHub → Settings → Secrets and variables → Actions :

| Secret | Valeur |
|--------|--------|
| `MAIL_SMTP_HOST` | `smtp.gmail.com` |
| `MAIL_SMTP_PORT` | `587` |
| `MAIL_SMTP_USER` | `ton.email@gmail.com` |
| `MAIL_SMTP_PASSWORD` | Mot de passe d'application Gmail |
| `HF_API_TOKEN` | Token HuggingFace |
| `MODEL_ID` | `mistralai/Mistral-7B-Instruct-v0.3` |
| `MAX_TOKENS` | `3000` |

### Lancement manuel

Tu peux déclencher manuellement via l'onglet **Actions** → **Sport Weekly Newsletter** → **Run workflow**.

## 🤝 Ajouter un ami

1. Crée un fichier `config/users/prenom.json`
2. Configure ses sports/équipes/joueurs
3. Commit & push — il recevra la newsletter au prochain lundi !

## 📁 Structure du projet

```
sport-weekly/
├── .github/workflows/     # GitHub Actions (envoi auto)
├── config/users/          # Configs utilisateurs (JSON)
├── src/
│   ├── fetch/             # Modules de récupération de données
│   │   ├── espn.py        # Client ESPN API générique
│   │   ├── football.py    # UCL + PSG
│   │   ├── rugby.py       # Top 14, Champions Cup, France, Sevens
│   │   ├── nba.py         # NBA + Wembanyama
│   │   ├── tennis.py      # ATP, Grand Chelems
│   │   ├── motorsport.py  # F1 + MotoGP
│   │   ├── cycling.py     # ProCyclingStats
│   │   ├── winter_sports.py # Biathlon + Ski
│   │   ├── sailing.py     # SailGP + Vendée Globe
│   │   ├── endurance.py   # Trail, Athlétisme, Natation
│   │   └── olympics.py    # JO
│   ├── model/
│   │   └── hf_client.py   # HuggingFace Inference API
│   └── send/
│       ├── mailer.py      # SMTP email
│       └── render.py      # Template HTML responsive
├── run.py                 # Point d'entrée CLI
├── requirements.txt
└── .env.example
```

## 📝 License

MIT — Fais-en ce que tu veux !
