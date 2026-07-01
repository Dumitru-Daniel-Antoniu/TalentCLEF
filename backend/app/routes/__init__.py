from fastapi import APIRouter

router = APIRouter()

from . import api  # noqa: E402,F401
