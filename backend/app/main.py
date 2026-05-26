from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.routes.api import router as api_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Job Resume Ranking API", version="0.1")

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
