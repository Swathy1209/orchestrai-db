"""
main.py — OrchestrAI Career Agent Entry Point
Runs on Render as a long-lived background worker.

Flow:
  Local .env  →  GitHub YAML DB  →  Render (scheduled runner)  →  Gmail email
"""

import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("OrchestrAI")


# ── Validate required env vars before starting ────────────────────────────────
REQUIRED_VARS = [
    "GITHUB_TOKEN",
    "GITHUB_USERNAME",
    "GITHUB_REPO",
    "EMAIL_USER",
    "EMAIL_PASS",
    "EMAIL_RECEIVER",
]


def _check_env() -> None:
    missing = [v for v in REQUIRED_VARS if not os.getenv(v)]
    if missing:
        logger.error("Missing required environment variables: %s", ", ".join(missing))
        logger.error("Set them in Render Dashboard → Environment, or in your .env file.")
        sys.exit(1)
    logger.info("All required environment variables are present ✓")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    _check_env()

    from backend.agents.career_agent import run_career_agent
    from backend.scheduler import schedule_daily_internship_email, run_once_now

    # Pass --now flag to run immediately (useful for testing on Render)
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        logger.info("Manual trigger: running career agent immediately...")
        run_once_now(run_career_agent)
    else:
        logger.info("Starting scheduler: career agent will run daily at 9:30 AM IST.")
        schedule_daily_internship_email(run_career_agent, hour=9, minute=30)
