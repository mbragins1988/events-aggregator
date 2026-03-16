# app/main.py (минимальная версия)
import sys
import logging
from fastapi import FastAPI
from app.presentation.api import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True,
)

logger = logging.getLogger(__name__)

app = FastAPI(title="Events Aggregator")
app.include_router(router)

@app.get("/")
async def root():
    return {"service": "Events Aggregator", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "ok"}