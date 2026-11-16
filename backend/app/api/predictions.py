
"""
CyberAgent AI prediction API.

POST /api/v1/predict
GET  /api/v1/model-info
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/v1", tags=["Predictions"])


class PredictionRequest(BaseModel):
    features: dict[str, Any] = Field(
        description="CICFlowMeter-compatible feature values"
    )


class PredictionResponse(BaseModel):
    model: str
    prediction: int
    label: str
    attack_score: float
    threshold: float


@router.get("/model-info")
def get_model_info(request: Request):
    predictor = request.app.state.predictor

    return {
        "model": predictor.model_name,
        "feature_count": len(predictor.features),
        "required_features": predictor.features,
        "threshold": predictor.threshold,
    }


@router.post(
    "/predict",
    response_model=PredictionResponse,
)
def predict(
    payload: PredictionRequest,
    request: Request,
):
    predictor = request.app.state.predictor

    try:
        return predictor.predict(payload.features)

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
