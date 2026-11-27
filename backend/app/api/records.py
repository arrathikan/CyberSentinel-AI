"""Prediction history and security alert management."""

from datetime import datetime
from enum import Enum
from typing import Annotated, Generic, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.database.models import AlertStatusChange, Prediction, SecurityAlert
from backend.app.database.session import get_db

router = APIRouter(prefix="/api/v1", tags=["Prediction history and alerts"])
Database = Annotated[Session, Depends(get_db)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]
AlertID = Annotated[int, Path(ge=1, le=2147483647)]


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Status(str, Enum):
    open = "open"
    investigating = "investigating"
    resolved = "resolved"
    closed = "closed"


TRANSITIONS = {
    Status.open: {Status.investigating},
    Status.investigating: {Status.open, Status.resolved},
    Status.resolved: {Status.investigating, Status.closed},
    Status.closed: set(),
}


class PredictionRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_name: str
    prediction: int
    attack_score: float
    threshold: float
    created_at: datetime


class AlertRecord(BaseModel):
    id: int
    prediction_id: int
    severity: Severity
    status: Status
    created_at: datetime


class StatusChange(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    previous_status: Status
    new_status: Status
    created_at: datetime


class AlertDetail(AlertRecord):
    prediction: PredictionRecord
    status_history: list[StatusChange]


class StatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Status


Record = TypeVar("Record")


class Page(BaseModel, Generic[Record]):
    items: list[Record]
    total: int
    limit: int
    offset: int


def alert_record(alert: SecurityAlert) -> AlertRecord:
    return AlertRecord(
        id=alert.id,
        prediction_id=alert.prediction_id,
        severity=alert.severity.lower(),
        status=alert.status.lower(),
        created_at=alert.created_at,
    )


def alert_detail(db: Session, alert: SecurityAlert) -> AlertDetail:
    changes = db.scalars(
        select(AlertStatusChange)
        .where(AlertStatusChange.alert_id == alert.id)
        .order_by(AlertStatusChange.id)
    )
    return AlertDetail(
        **alert_record(alert).model_dump(),
        prediction=PredictionRecord.model_validate(alert.prediction),
        status_history=[StatusChange.model_validate(change) for change in changes],
    )


@router.get("/predictions")
def prediction_history(db: Database, limit: Limit = 50, offset: Offset = 0) -> Page[PredictionRecord]:
    rows = db.scalars(
        select(Prediction).order_by(Prediction.created_at.desc(), Prediction.id.desc())
        .limit(limit).offset(offset)
    )
    return Page(
        items=[PredictionRecord.model_validate(row) for row in rows],
        total=db.scalar(select(func.count()).select_from(Prediction)),
        limit=limit,
        offset=offset,
    )


@router.get("/alerts")
def list_alerts(
    db: Database,
    limit: Limit = 50,
    offset: Offset = 0,
    severity: Severity | None = None,
    status: Status | None = None,
) -> Page[AlertRecord]:
    filters = []
    if severity is not None:
        filters.append(SecurityAlert.severity.in_((severity.value, severity.value.upper())))
    if status is not None:
        filters.append(SecurityAlert.status.in_((status.value, status.value.upper())))
    rows = db.scalars(
        select(SecurityAlert).where(*filters)
        .order_by(SecurityAlert.created_at.desc(), SecurityAlert.id.desc())
        .limit(limit).offset(offset)
    )
    return Page(
        items=[alert_record(row) for row in rows],
        total=db.scalar(select(func.count()).select_from(SecurityAlert).where(*filters)),
        limit=limit,
        offset=offset,
    )


@router.get("/alerts/{alert_id}")
def get_alert(alert_id: AlertID, db: Database) -> AlertDetail:
    alert = db.get(SecurityAlert, alert_id)
    if alert is None:
        raise HTTPException(404, "Alert not found")
    return alert_detail(db, alert)


@router.patch("/alerts/{alert_id}/status")
def update_alert_status(alert_id: AlertID, payload: StatusUpdate, db: Database) -> AlertDetail:
    with db.begin():
        alert = db.scalar(
            select(SecurityAlert).where(SecurityAlert.id == alert_id).with_for_update()
        )
        if alert is None:
            raise HTTPException(404, "Alert not found")
        previous = Status(alert.status.lower())
        if previous != payload.status:
            if payload.status not in TRANSITIONS[previous]:
                raise HTTPException(409, "Invalid alert status transition")
            alert.status = payload.status.value
            db.add(AlertStatusChange(
                alert_id=alert.id, previous_status=previous.value, new_status=alert.status,
            ))
            db.flush()
        return alert_detail(db, alert)
