from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging
import time

from app.routes.api import router as api_router
from app.ml.embeddings import get_model_info

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    started_at = time.perf_counter()
    logger.info("Loading ranking model before accepting requests...")
    try:
        model_info = await asyncio.to_thread(get_model_info)
    except Exception:
        logger.exception("Ranking model warm-up failed; requests will retry lazy loading")
        model_info = {"loaded": False}
    elapsed = time.perf_counter() - started_at
    if model_info.get("loaded"):
        logger.info(
            "Ranking model ready at startup (type=%s, dim=%s, %.2fs)",
            model_info.get("model_type"),
            model_info.get("dim", "unknown"),
            elapsed,
        )
    else:
        logger.warning("Ranking model did not load during startup (%.2fs)", elapsed)
    yield


app = FastAPI(title="Job Resume Ranking API", version="0.1", lifespan=lifespan)

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    return {"status": "ok", "service": "Job Resume Ranking API"}
