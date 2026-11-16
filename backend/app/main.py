
"""
CyberAgent AI - FastAPI application.

Loads the selected machine learning model at startup.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.api.predictions import router
from backend.app.ml.inference import CyberattackPredictor


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the model once at application startup.
    app.state.predictor = CyberattackPredictor()

    yield

    # Release reference on application shutdown.
    del app.state.predictor


app = FastAPI(
    title="CyberAgent AI",
    description="AI-Powered Cyberattack Detection API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/")
def home():
    return {
        "project": "CyberAgent AI",
        "message": "CyberAgent backend is running",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": True,
    }
