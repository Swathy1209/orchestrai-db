"""
skill_agent.py — Skill Gap Analysis Agent
OrchestrAI Autonomous Multi-Agent System

Flow:
  1. Download resume PDF from GitHub
  2. Extract text from PDF
  3. Extract skills from text (OpenAI)
  4. Store extracted skills to database/users.yaml
  5. Read jobs.yaml from GitHub
  6. Detect skill gaps (missing_skills = job_skills - resume_skills)
  7. Generate learning roadmap via OpenAI
  8. Store skill_gap.yaml to GitHub
  9. Log agent activity to agent_logs.yaml
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from backend.github_yaml_db import (
    read_yaml_from_github,
    write_yaml_to_github,
    append_log_entry,
)
from backend.utils.resume_parser import download_and_extract
from backend.utils.ai_engine import extract_skills_using_ai, generate_learning_roadmap

logger = logging.getLogger("OrchestrAI.SkillAgent")

USERS_FILE     = "database/users.yaml"
JOBS_FILE      = "database/jobs.yaml"
SKILL_GAP_FILE = "database/skill_gap.yaml"


# ==============================================================================
# Helper functions for database interaction
# ==============================================================================

def store_user_skills_yaml(skills: list[str]) -> bool:
    """
    Store extracted skills into database/users.yaml on GitHub.
    Overrides existing resume_skills.
    """
    analyzed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    
    # We maintain a standard user base - swathiga
    data = {
        "user": {
            "name": "swathiga",
            "email": "swathigasundararajan@gmail.com",
            "resume_skills": skills,
            "extracted_at": analyzed_at
        }
    }
    
    try:
        ok = write_yaml_to_github(USERS_FILE, data)
        if ok:
            logger.info("SkillAgent: Stored %d skills gracefully in %s.", len(skills), USERS_FILE)
        return ok
    except Exception as exc:
        logger.error("SkillAgent: store_user_skills_yaml failed - %s", exc)
        return False


def read_jobs_yaml() -> list[dict]:
    """Read jobs.yaml from GitHub."""
    try:
        data = read_yaml_from_github(JOBS_FILE)
        jobs = data.get("jobs", [])
        if not isinstance(jobs, list):
            return []
        logger.info("SkillAgent: Read %d jobs from '%s'.", len(jobs), JOBS_FILE)
        return jobs
    except Exception as exc:
        logger.error("SkillAgent: read_jobs_yaml failed - %s", exc)
        return []


def detect_skill_gap(resume_skills: list[str], jobs: list[dict]) -> tuple[list[str], list[str]]:
    """
    Compute missing_skills = union(job technical_skills) - resume_skills.
    """
    job_skills: set[str] = set()
    for job in jobs:
        for s in job.get("technical_skills", []):
            if s and str(s).strip():
                job_skills.add(str(s).strip())
                
    user_lower = {s.lower() for s in resume_skills}
    missing = sorted({s for s in job_skills if s.lower() not in user_lower})
    logger.info("SkillAgent: %d job skills needed, %d missing.", len(job_skills), len(missing))
    return sorted(job_skills), missing


def store_skill_gap_yaml(
    resume_skills: list[str],
    missing_skills: list[str],
    roadmap: list[str],
) -> bool:
    """Write skill gaps and roadmap to database/skill_gap.yaml on GitHub."""
    analyzed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    data = {
        "skill_analysis": {
            "user": "swathiga",
            "current_skills": resume_skills,
            "missing_skills": missing_skills,
            "recommended_learning_roadmap": roadmap,
            "analyzed_at": analyzed_at,
        }
    }
    try:
        ok = write_yaml_to_github(SKILL_GAP_FILE, data)
        if ok:
            logger.info(
                "SkillAgent: %s written (%d missing, %d steps).", 
                SKILL_GAP_FILE, len(missing_skills), len(roadmap)
            )
        return ok
    except Exception as exc:
        logger.error("SkillAgent: store_skill_gap_yaml failed - %s", exc)
        return False


def log_agent_activity(action: str, details: Optional[str] = None, status: str = "success") -> bool:
    """Append a log entry to database/agent_logs.yaml."""
    entry = {
        "agent": "SkillAgent",
        "action": action,
        "status": status,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
    }
    if details:
        entry["details"] = details
    try:
        return append_log_entry(entry)
    except Exception as exc:
        logger.error("SkillAgent: log_agent_activity failed - %s", exc)
        return False


# ==============================================================================
# Main Orchestrator (run_skill_agent)
# ==============================================================================

def run_skill_agent() -> dict:
    """
    Execute full SkillAgent pipeline.
    Does NOT send email! Outputs JSON format needed by ExecutionAgent.
    """
    logger.info("SkillAgent: Starting Skill Agent...")
    log_agent_activity("SkillAgent run initiated")
    
    result = {
        "resume_skills": [],
        "missing_skills": [],
        "roadmap": [],
        "analyzed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "status": "error"
    }
    
    try:
        # Step 1 & 2: Download and parse resume
        resume_text = download_and_extract()
        if not resume_text:
            log_agent_activity("Resume extraction failed", status="error")
            result["status"] = "error"
            return result
            
        logger.info("SkillAgent: Resume parsed successfully.")
        log_agent_activity("Resume downloaded and parsed")

        # Step 3: Extract skills with AI
        resume_skills = extract_skills_using_ai(resume_text)
        result["resume_skills"] = resume_skills
        if not resume_skills:
            logger.warning("SkillAgent: No skills extracted from resume.")
            
        # Step 4: Store skills in users.yaml
        if not store_user_skills_yaml(resume_skills):
            logger.error("SkillAgent: Failed to store users.yaml.")
            
        # Step 5: Read jobs
        jobs = read_jobs_yaml()
        if not jobs:
            log_agent_activity("Skill analysis skipped - no jobs found in database", status="partial")
            result["status"] = "partial"
            return result

        # Step 6: Detect skill gaps
        _, missing_skills = detect_skill_gap(resume_skills, jobs)
        result["missing_skills"] = missing_skills

        # Step 7: Generate roadmap
        roadmap = generate_learning_roadmap(resume_skills, missing_skills)
        result["roadmap"] = roadmap

        # Step 8: Store skill gap data
        if not store_skill_gap_yaml(resume_skills, missing_skills, roadmap):
            logger.error("SkillAgent: Failed writing skill_gap.yaml.")
            result["status"] = "error"
            return result

        # Step 9: Log success
        log_agent_activity("Skill gap analysis complete", f"Missing skills: {len(missing_skills)}")
        
        result["status"] = "success"
        result["analyzed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        logger.info("SkillAgent: Completed successfully.")
        
        # Step 10: Return payload
        return result

    except Exception as exc:
        logger.exception("SkillAgent: Pipeline crashed - %s", exc)
        log_agent_activity("Exception in SkillAgent", str(exc), "error")
        result["status"] = "error"
        return result


if __name__ == "__main__":
    import json, sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    res = run_skill_agent()
    print("\n--- SkillAgent Output ---")
    print(json.dumps(res, indent=2, ensure_ascii=False))
