"""Simple in-memory storage for demo purposes.

In-memory dictionaries keep uploaded resumes and job descriptions. This is
intentionally simple for the demo; swap for a DB or persistent store in prod.
"""
from typing import Dict, Optional

RESUMES: Dict[str, Dict] = {}
JOBS: Dict[str, Dict] = {}


def save_resume(rid: str, filename: str, text: str):
    RESUMES[rid] = {"id": rid, "filename": filename, "text": text}


def get_resume(rid: str) -> Optional[Dict]:
    return RESUMES.get(rid)


def list_resumes():
    return list(RESUMES.values())


def save_job(jid: str, text: str, embedding):
    JOBS[jid] = {"id": jid, "text": text, "embedding": embedding}


def get_job(jid: str):
    return JOBS.get(jid)
