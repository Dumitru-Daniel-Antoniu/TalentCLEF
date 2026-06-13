from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi import status
from typing import List, Optional
from uuid import uuid4
import os
from pathlib import Path
import logging

from app.services import storage, parser
from app.ml.embeddings import embed_texts, get_embedding, get_model_info
from app.utils.text import extract_skills, clean_text, summarize_text
from app.schemas.schemas import UploadResponse, JobCreate, RankRequest

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload-resumes", response_model=List[UploadResponse])
async def upload_resumes(files: List[UploadFile] = File(...), job_id: Optional[str] = Form(None)):
    """Accept multiple resume files (PDF/DOCX/TXT), extract text, and store temporarily."""
    upload_dir = Path(os.environ.get("UPLOAD_DIR", "uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)

    responses = []
    for f in files:
        try:
            contents = await f.read()
            uid = uuid4().hex
            ext = Path(f.filename).suffix or ""
            dest = upload_dir / f"{uid}{ext}"
            dest.write_bytes(contents)

            text = parser.parse_resume(dest)
            storage.save_resume(uid, f.filename, text, job_id=job_id)

            skills = list(extract_skills(text))
            summary = summarize_text(text)

            responses.append(
                UploadResponse(id=uid, filename=f.filename, snippet=(text[:400] + '...') if len(text) > 400 else text, skills=skills, summary=summary)
            )
        except Exception as e:
            logger.exception("Failed to process upload: %s", e)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return responses


@router.get("/resumes")
async def list_resumes(job_id: Optional[str] = None):
    """List uploaded resumes; optionally filter by job_id."""
    try:
        if job_id:
            return storage.list_resumes_for_job(job_id)
        return storage.list_resumes()
    except Exception as e:
        logger.exception("Failed to list resumes: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/job-description-file")
async def job_description_file(file: UploadFile = File(...)):
    """Accept a job description file (PDF/DOCX/TXT), extract text, and store embedding."""
    upload_dir = Path(os.environ.get("UPLOAD_DIR", "uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)

    try:
        contents = await file.read()
        uid = uuid4().hex
        ext = Path(file.filename).suffix or ""
        dest = upload_dir / f"{uid}{ext}"
        dest.write_bytes(contents)

        text = parser.parse_resume(dest)
        text_clean = clean_text(text)
        emb = get_embedding(text_clean)
        job_id = uuid4().hex
        storage.save_job(job_id, text_clean, emb)

        skills = list(extract_skills(text_clean))
        summary = summarize_text(text_clean)

        return {
            "job_id": job_id,
            "dim": emb.shape[0],
            "filename": file.filename,
            "snippet": (text_clean[:400] + "...") if len(text_clean) > 400 else text_clean,
            "skills": skills,
            "summary": summary,
        }
    except Exception as e:
        logger.exception("Failed to process job upload: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/job-description")
async def job_description(payload: JobCreate):
    """Accept a job description, preprocess and store its embedding."""
    text = clean_text(payload.text)
    emb = get_embedding(text)
    job_id = uuid4().hex
    storage.save_job(job_id, text, emb)
    return {"job_id": job_id, "dim": emb.shape[0]}


@router.get("/job/{job_id}")
async def get_job(job_id: str):
    """Return stored job description text for the given job_id."""
    try:
        job = storage.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"job_id": job_id, "text": job.get("text", "")}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to fetch job: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resume/{resume_id}")
async def get_resume(resume_id: str):
    """Return stored resume text for the given resume id."""
    try:
        r = storage.get_resume(resume_id)
        if not r:
            raise HTTPException(status_code=404, detail="Resume not found")
        return {"id": r["id"], "filename": r.get("filename", ""), "text": r.get("text", "")}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to fetch resume: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rank")
async def rank(payload: RankRequest):
    """Compare job (by id or raw text) with stored resumes and return ranked candidates."""
    # Get job embedding
    if payload.job_text:
        job_text = clean_text(payload.job_text)
        job_emb = get_embedding(job_text)
    elif payload.job_id:
        job = storage.get_job(payload.job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        job_emb = job["embedding"]
    else:
        raise HTTPException(status_code=400, detail="Provide job_text or job_id")

    # Select resumes
    resumes = []
    if payload.resume_ids:
        for rid in payload.resume_ids:
            r = storage.get_resume(rid)
            if r:
                resumes.append(r)
    else:
        resumes = storage.list_resumes()

    if not resumes:
        raise HTTPException(status_code=404, detail="No resumes available to rank")

    texts = [r["text"] for r in resumes]
    names = [r["filename"] for r in resumes]
    ids = [r["id"] for r in resumes]

    # Compute embeddings for resumes
    try:
        embs = embed_texts(texts)
    except Exception as e:
        logger.exception("Embedding error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    # Cosine similarity
    try:
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity

        job_emb_arr = np.array(job_emb).reshape(1, -1)
        sim = cosine_similarity(job_emb_arr, embs)[0]
    except Exception as e:
        logger.exception("Similarity error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    results = []
    for idx, s in enumerate(sim):
        text = texts[idx]
        skills = list(extract_skills(text))
        summary = summarize_text(text)
        results.append({
            "id": ids[idx],
            "name": names[idx],
            "score": float(s),
            "score_pct": float(round(float(s) * 100.0, 2)),
            "skills": skills,
            "summary": summary,
        })

    # Sort by score desc
    results = sorted(results, key=lambda r: r["score"], reverse=True)

    top_k = payload.top_k or len(results)
    return {"rankings": results[:top_k], "total": len(results)}



@router.get("/model")
async def model_status():
    """Return model loader status and basic info."""
    try:
        info = get_model_info()
        return info
    except Exception as e:
        logger.exception("Failed to get model info: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
