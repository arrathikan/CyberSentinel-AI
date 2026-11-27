
"""
CyberAgent AI prediction API.

POST /api/v1/predict
GET  /api/v1/model-info
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, FiniteFloat


from backend.app.api.correlation import FlowMetadata, correlate_alert
from backend.app.api.records import Database
from backend.app.database.models import Prediction, SecurityAlert


router = APIRouter(prefix="/api/v1", tags=["Predictions"])


class PredictionRequest(BaseModel):
    features: dict[str, Annotated[FiniteFloat, Field(strict=True)] | None] = Field(
        description="CICFlowMeter-compatible feature values"
    )
    metadata: FlowMetadata | None = None


class PredictionResponse(BaseModel):
    prediction_id: int
    alert_id: int | None
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
    db: Database,
):
    predictor = request.app.state.predictor

    try:
        result = predictor.predict(payload.features)

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    with db.begin():
        record = Prediction(
            model_name=result["model"],
            model_version=predictor.model_version,
            prediction=result["prediction"],
            attack_score=result["attack_score"],
            threshold=result["threshold"],
        )
        db.add(record)
        alert = None
        if record.prediction == 1:
            alert = SecurityAlert(
                prediction=record,
                severity=request.app.state.severity_policy.classify(record.attack_score),
            )
            db.add(alert)
        db.flush()
        if alert is not None:
            correlate_alert(db, alert, payload.metadata, request.app.state.correlation_policy)
        return PredictionResponse(
            **result, prediction_id=record.id, alert_id=alert.id if alert else None,
        )
