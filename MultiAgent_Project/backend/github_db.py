"""
github_db.py — GitHub REST API Cloud Database Handler
OrchestrAI Autonomous Multi-Agent System

Handles:
  - Reading/writing jobs.json from GitHub
  - Reading/writing agent_logs.json from GitHub
  - Append-only logic (no overwrites)
"""

import os
import json
import base64
import logging
import requests
from datetime import datetime, timezone
from typing import Any
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("CareerAgent.GitHubDB")

GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO: str  = os.getenv("GITHUB_REPO", "")          # e.g. "username/orchestrai-db"
GITHUB_BRANCH: str = os.getenv("GITHUB_BRANCH", "main")

JOBS_FILE_PATH: str = "jobs.json"
LOGS_FILE_PATH: str = "agent_logs.json"

_BASE_URL = "https://api.github.com"

# ──────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────

def _headers() -> dict[str, str]:
    """Return authenticated request headers."""
    if not GITHUB_TOKEN:
        raise EnvironmentError("GITHUB_TOKEN is not set in environment.")
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _get_file(path: str) -> tuple[list | dict, str]:
    """
    Fetch a JSON file from the GitHub repo.
    Returns (parsed_content, sha).
    sha is needed for subsequent PUT requests.
    """
    url = f"{_BASE_URL}/repos/{GITHUB_REPO}/contents/{path}"
    resp = requests.get(url, headers=_headers(), params={"ref": GITHUB_BRANCH}, timeout=15)

    if resp.status_code == 404:
        # File doesn't exist yet — return empty data, no sha
        logger.info("GitHubDB: '%s' not found — will create on first write.", path)
        return ([] if path == JOBS_FILE_PATH else {}), ""

    resp.raise_for_status()
    data = resp.json()
    raw = base64.b64decode(data["content"]).decode("utf-8")
    sha = data.get("sha", "")
    return json.loads(raw), sha


def _put_file(path: str, content: list | dict, sha: str, commit_message: str) -> bool:
    """
    Create or update a JSON file in the GitHub repo.
    Returns True on success.
    """
    url = f"{_BASE_URL}/repos/{GITHUB_REPO}/contents/{path}"
    encoded = base64.b64encode(json.dumps(content, indent=2, ensure_ascii=False).encode()).decode()

    payload: dict[str, Any] = {
        "message": commit_message,
        "content": encoded,
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha  # required for updates

    resp = requests.put(url, headers=_headers(), json=payload, timeout=20)
    resp.raise_for_status()
    logger.info("GitHubDB: '%s' updated successfully.", path)
    return True


# ──────────────────────────────────────────────
# Jobs API
# ──────────────────────────────────────────────

def read_jobs_from_github() -> list[dict]:
    """
    Read the full jobs list from jobs.json in the GitHub cloud database.
    Returns a list of job dicts (empty list if file doesn't exist yet).
    """
    try:
        jobs, _ = _get_file(JOBS_FILE_PATH)
        if not isinstance(jobs, list):
            logger.warning("GitHubDB: jobs.json is not a list — resetting.")
            return []
        logger.info("GitHubDB: Read %d existing jobs.", len(jobs))
        return jobs
    except Exception as exc:
        logger.error("GitHubDB: Failed to read jobs — %s", exc)
        return []


def write_jobs_to_github(jobs: list[dict]) -> bool:
    """
    Overwrite jobs.json entirely. Use append_new_jobs() for safe upsert logic.
    """
    try:
        _, sha = _get_file(JOBS_FILE_PATH)
        return _put_file(
            JOBS_FILE_PATH,
            jobs,
            sha,
            f"chore(jobs): full update — {datetime.now(timezone.utc).isoformat()}",
        )
    except Exception as exc:
        logger.error("GitHubDB: Failed to write jobs — %s", exc)
        return False


def append_new_jobs(new_jobs: list[dict]) -> tuple[int, int]:
    """
    Merge new_jobs into GitHub jobs.json without overwriting existing entries.
    Deduplication key: (company + role + source).

    Returns (jobs_added, total_jobs).
    """
    try:
        existing_jobs, sha = _get_file(JOBS_FILE_PATH)
        if not isinstance(existing_jobs, list):
            existing_jobs = []

        # Build a set of unique keys for dedup
        existing_keys: set[str] = {
            f"{j.get('company','')}|{j.get('role','')}|{j.get('source','')}"
            for j in existing_jobs
        }

        added = 0
        for job in new_jobs:
            key = f"{job.get('company','')}|{job.get('role','')}|{job.get('source','')}"
            if key not in existing_keys:
                existing_jobs.append(job)
                existing_keys.add(key)
                added += 1

        if added > 0:
            _put_file(
                JOBS_FILE_PATH,
                existing_jobs,
                sha,
                f"feat(jobs): appended {added} new internships — {datetime.now(timezone.utc).isoformat()}",
            )
            logger.info("GitHubDB: Appended %d new jobs. Total: %d.", added, len(existing_jobs))
        else:
            logger.info("GitHubDB: No new jobs to append. Total unchanged: %d.", len(existing_jobs))

        return added, len(existing_jobs)

    except Exception as exc:
        logger.error("GitHubDB: append_new_jobs failed — %s", exc)
        return 0, 0


# ──────────────────────────────────────────────
# Logs API
# ──────────────────────────────────────────────

def append_log_entry(entry: dict) -> bool:
    """
    Append a single log entry to agent_logs.json in GitHub.
    Entry format: { "timestamp": "...", "level": "INFO", "message": "..." }
    """
    try:
        logs, sha = _get_file(LOGS_FILE_PATH)
        if not isinstance(logs, dict):
            logs = {"entries": []}

        logs.setdefault("entries", [])
        logs["entries"].append({
            **entry,
            "timestamp": entry.get("timestamp", datetime.now(timezone.utc).isoformat()),
        })
        # Keep last 500 entries to avoid file bloat
        logs["entries"] = logs["entries"][-500:]
        logs["last_updated"] = datetime.now(timezone.utc).isoformat()

        return _put_file(
            LOGS_FILE_PATH,
            logs,
            sha,
            f"log: agent activity — {datetime.now(timezone.utc).isoformat()}",
        )
    except Exception as exc:
        logger.error("GitHubDB: append_log_entry failed — %s", exc)
        return False


def read_logs_from_github() -> list[dict]:
    """Read all log entries from GitHub agent_logs.json."""
    try:
        logs, _ = _get_file(LOGS_FILE_PATH)
        return logs.get("entries", []) if isinstance(logs, dict) else []
    except Exception as exc:
        logger.error("GitHubDB: Failed to read logs — %s", exc)
        return []
