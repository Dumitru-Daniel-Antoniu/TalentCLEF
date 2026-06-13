"""Simple in-memory storage for demo purposes.

In-memory dictionaries keep uploaded resumes and job descriptions. This is
intentionally simple for the demo; swap for a DB or persistent store in prod.
"""
from typing import Dict, Optional

RESUMES: Dict[str, Dict] = {}
JOBS: Dict[str, Dict] = {}


def save_resume(rid: str, filename: str, text: str, job_id: Optional[str] = None):
    RESUMES[rid] = {"id": rid, "filename": filename, "text": text, "job_id": job_id}


def get_resume(rid: str) -> Optional[Dict]:
    return RESUMES.get(rid)


def list_resumes():
    return list(RESUMES.values())


def list_resumes_for_job(job_id: str):
    return [r for r in RESUMES.values() if r.get("job_id") == job_id]


def save_job(jid: str, text: str, embedding):
    JOBS[jid] = {"id": jid, "text": text, "embedding": embedding}


def get_job(jid: str):
    return JOBS.get(jid)
