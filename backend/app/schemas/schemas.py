from pydantic import BaseModel
from typing import List, Optional


class UploadResponse(BaseModel):
    id: str
    filename: str
    snippet: str
    skills: List[str] = []
    summary: str


class JobCreate(BaseModel):
    text: str


class RankRequest(BaseModel):
    job_text: Optional[str] = None
    job_id: Optional[str] = None
    resume_ids: Optional[List[str]] = None
    top_k: Optional[int] = 10
