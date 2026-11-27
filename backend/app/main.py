
"""
CyberAgent AI - FastAPI application.

Loads the selected machine learning model at startup.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from backend.app.api.correlation import CorrelationPolicy
from backend.app.api.incidents import router as incidents_router
from backend.app.api.predictions import router
from backend.app.api.records import router as records_router
from backend.app.api.severity import SeverityPolicy
from backend.app.database.session import check_db_health
from backend.app.ml.inference import CyberattackPredictor



@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.correlation_policy = CorrelationPolicy.from_environment()
    app.state.severity_policy = SeverityPolicy.from_environment()
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
app.include_router(records_router)
app.include_router(incidents_router)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    if request.url.path == "/api/v1/predict":
        # Validation errors can otherwise echo submitted network identifiers.
        errors = [
            {"loc": error["loc"], "msg": error["msg"], "type": error["type"]}
            for error in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": errors})
    return await request_validation_exception_handler(request, exc)


@app.exception_handler(SQLAlchemyError)
async def handle_database_error(request: Request, exc: SQLAlchemyError):
    logging.getLogger(__name__).error("Database request failed (%s)", type(exc).__name__)
    return JSONResponse(status_code=503, content={"detail": "Database operation failed"})


@app.get("/")
def home():
    return {
        "project": "CyberAgent AI",
        "message": "CyberAgent backend is running",
    }


@app.get("/health")
def health():
    db_health = check_db_health()
    return {
        "status": "ok",
        "model_loaded": True,
        "database": db_health,
    }
