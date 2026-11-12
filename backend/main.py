
import logging

from fastapi import FastAPI
from pydantic import BaseModel

from backend.logging_config import configure_logging
from backend.routes.monitoring import router as monitoring_router
from backend.routes.requests import router as requests_router


configure_logging()
logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: str
    service: str


class RootResponse(BaseModel):
    message: str
    service: str
    version: str


app = FastAPI(
    title="Health Pre-Authorisation Desk",
    description=(
        "A multi-agent AI system for assisting "
        "health insurance pre-authorisation assessment."
    ),
    version="1.0.0",
)

app.include_router(requests_router)
app.include_router(monitoring_router)


@app.get("/", response_model=RootResponse)
async def root():
    logger.info("Root endpoint accessed")

    return {
        "message": "Welcome to Health Pre-Authorisation Desk",
        "service": "Health Pre-Authorisation Desk API",
        "version": "1.0.0",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    logger.info("Health check accessed")

    return {
        "status": "ok",
        "service": "Health Pre-Authorisation Desk API",
    }
