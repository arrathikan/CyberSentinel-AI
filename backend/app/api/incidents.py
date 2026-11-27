"""Read-only incident APIs."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path
from pydantic import AfterValidator, BaseModel, ConfigDict
from sqlalchemy import func, select

from backend.app.api.correlation import utc
from backend.app.api.records import (
    AlertID, AlertRecord, Database, Limit, Offset, Page, Severity, Status, alert_record,
)
from backend.app.database.models import Incident, IncidentAlert, SecurityAlert

router = APIRouter(prefix="/api/v1", tags=["Incidents"])
IncidentID = Annotated[int, Path(ge=1, le=2147483647)]
UtcDatetime = Annotated[datetime, AfterValidator(utc)]


class IncidentRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    status: Status
    severity: Severity
    first_seen_at: UtcDatetime
    last_seen_at: UtcDatetime
    created_at: UtcDatetime
    updated_at: UtcDatetime


class IncidentMember(BaseModel):
    alert: AlertRecord
    observed_at: UtcDatetime
    correlation_reason: str


class AlertIncident(BaseModel):
    incident: IncidentRecord
    correlation_reason: str


@router.get("/incidents")
def incidents(
    db: Database,
    limit: Limit = 50,
    offset: Offset = 0,
    status: Status | None = None,
    severity: Severity | None = None,
) -> Page[IncidentRecord]:
    filters = []
    if status is not None:
        filters.append(Incident.status == status.value)
    if severity is not None:
        filters.append(Incident.severity == severity.value)
    rows = db.scalars(
        select(Incident).where(*filters)
        .order_by(Incident.last_seen_at.desc(), Incident.id.desc())
        .limit(limit).offset(offset)
    )
    return Page(
        items=[IncidentRecord.model_validate(row) for row in rows],
        total=db.scalar(select(func.count()).select_from(Incident).where(*filters)),
        limit=limit, offset=offset,
    )


@router.get("/incidents/{incident_id}")
def incident_detail(incident_id: IncidentID, db: Database) -> IncidentRecord:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(404, "Incident not found")
    return IncidentRecord.model_validate(incident)


@router.get("/incidents/{incident_id}/alerts")
def incident_alerts(
    incident_id: IncidentID, db: Database, limit: Limit = 50, offset: Offset = 0,
) -> Page[IncidentMember]:
    if db.get(Incident, incident_id) is None:
        raise HTTPException(404, "Incident not found")
    member_filter = IncidentAlert.incident_id == incident_id
    rows = db.execute(
        select(SecurityAlert, IncidentAlert)
        .join(IncidentAlert, IncidentAlert.alert_id == SecurityAlert.id)
        .where(member_filter)
        .order_by(IncidentAlert.observed_at, IncidentAlert.id)
        .limit(limit).offset(offset)
    )
    return Page(
        items=[
            IncidentMember(
                alert=alert_record(alert), observed_at=member.observed_at,
                correlation_reason=member.correlation_reason,
            )
            for alert, member in rows
        ],
        total=db.scalar(select(func.count()).select_from(IncidentAlert).where(member_filter)),
        limit=limit, offset=offset,
    )


@router.get("/alerts/{alert_id}/incident")
def alert_incident(alert_id: AlertID, db: Database) -> AlertIncident:
    row = db.execute(
        select(Incident, IncidentAlert.correlation_reason)
        .join(IncidentAlert, IncidentAlert.incident_id == Incident.id)
        .where(IncidentAlert.alert_id == alert_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(404, "Alert has no associated incident")
    incident, reason = row
    return AlertIncident(incident=IncidentRecord.model_validate(incident), correlation_reason=reason)
