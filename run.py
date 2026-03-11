"""Sport Weekly — CLI entry point."""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def main():
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "test"

    if mode == "test":
        print("🧪 Mode TEST (dry run — pas d'envoi d'email)")
        from src.main import run
        try:
            run(dry_run=True)
        except Exception as e:
            logging.error("Test run failed: %s", e, exc_info=True)
            sys.exit(0)

    elif mode == "once":
        print("▶️  Exécution unique — envoi des newsletters")
        from src.main import run
        try:
            run(dry_run=False)
            print("✅ Newsletters envoyées !")
        except Exception as e:
            logging.error("Erreur: %s", e, exc_info=True)
            sys.exit(0)

    elif mode == "schedule":
        print("⏰ Mode SCHEDULER — exécution hebdomadaire")
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
        from src.config import Config
        from src.main import run

        cfg = Config()
        scheduler = BlockingScheduler(timezone=cfg.TIMEZONE)
        scheduler.add_job(
            run,
            CronTrigger(day_of_week="mon", hour=9, minute=0),
            id="weekly_newsletter",
            replace_existing=True,
        )
        print(f"📅 Newsletter planifiée : chaque Lundi à 09:00 ({cfg.TIMEZONE})")
        try:
            scheduler.start()
        except KeyboardInterrupt:
            print("\n⏹️  Scheduler arrêté")
            scheduler.shutdown()

    else:
        print("Usage: python run.py [test|once|schedule]")
        print()
        print("  test     — Dry run (pas d'email)")
        print("  once     — Exécuter une fois et envoyer")
        print("  schedule — Lancer le scheduler (chaque lundi 9h)")
        sys.exit(1)


if __name__ == "__main__":
    main()
