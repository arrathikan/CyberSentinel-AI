"""Metadata validation and transactional, deterministic incident assignment."""

import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, IPvAnyAddress, SecretStr
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.app.database.models import Incident, IncidentAlert, SecurityAlert


class FlowMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_ip: IPvAnyAddress | None = None
    destination_ip: IPvAnyAddress | None = None
    source_port: Annotated[int, Field(strict=True, ge=0, le=65535)] | None = None
    destination_port: Annotated[int, Field(strict=True, ge=0, le=65535)] | None = None
    protocol: Literal["tcp", "udp"] | None = None
    observed_at: AwareDatetime | None = None


class CorrelationPolicy(BaseModel):
    window_seconds: int = Field(default=300, ge=1, le=86400)
    secret: SecretStr | None = Field(default=None, min_length=32)

    @classmethod
    def from_environment(cls):
        values = {}
        if "INCIDENT_WINDOW_SECONDS" in os.environ:
            values["window_seconds"] = os.environ["INCIDENT_WINDOW_SECONDS"]
        if os.getenv("INCIDENT_CORRELATION_SECRET"):
            values["secret"] = SecretStr(os.environ["INCIDENT_CORRELATION_SECRET"])
        return cls.model_validate(values)


SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def utc(value: datetime) -> datetime:
    # SQLite fixtures return naive values for timezone-aware database columns.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def correlate_alert(
    db: Session,
    alert: SecurityAlert,
    metadata: FlowMetadata | None,
    policy: CorrelationPolicy,
) -> IncidentAlert | None:
    if metadata is None or policy.secret is None or metadata.observed_at is None:
        return None

    signals = (
        metadata.source_ip, metadata.destination_ip, metadata.destination_port, metadata.protocol,
    )
    if any(signal is None for signal in signals):
        return None

    observed_at = utc(metadata.observed_at)
    now = datetime.now(timezone.utc)
    if observed_at > now + timedelta(minutes=5):
        return None

    key = hmac.new(
        policy.secret.get_secret_value().encode(),
        json.dumps([str(signal) for signal in signals]).encode(),
        hashlib.sha256,
    ).hexdigest()

    # Lock the alert for reprocessing and serialize all writers for this flow key.
    db.scalar(select(SecurityAlert.id).where(SecurityAlert.id == alert.id).with_for_update())
    existing = db.scalar(select(IncidentAlert).where(IncidentAlert.alert_id == alert.id))
    if existing is not None:
        return existing
    if db.get_bind().dialect.name == "postgresql":
        lock_key = int.from_bytes(bytes.fromhex(key[:16]), "big", signed=True)
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})

    window = timedelta(seconds=policy.window_seconds)
    candidates = db.scalars(
        select(Incident)
        .where(
            Incident.correlation_key == key,
            Incident.status.in_(("open", "investigating")),
            Incident.last_seen_at >= observed_at - window,
            Incident.last_seen_at <= observed_at + window,
            Incident.first_seen_at >= observed_at - window,
        )
        .order_by(Incident.last_seen_at.desc(), Incident.id.desc())
    )
    incident = next((
        candidate for candidate in candidates
        if utc(candidate.last_seen_at) - utc(candidate.first_seen_at) <= window
    ), None)
    severity = alert.severity.lower()
    reason = "Started a new incident for the observed source and destination service."
    if incident is None:
        incident = Incident(
            correlation_key=key, title="Correlated network alerts", status="open",
            severity=severity, first_seen_at=observed_at, last_seen_at=observed_at,
            created_at=now, updated_at=now,
        )
        db.add(incident)
        db.flush()
    else:
        incident.first_seen_at = min(utc(incident.first_seen_at), observed_at)
        incident.last_seen_at = max(utc(incident.last_seen_at), observed_at)
        incident.severity = max(incident.severity, severity, key=SEVERITY_RANK.__getitem__)
        incident.updated_at = now
        reason = (
            "Matched source IP, destination IP, destination port and protocol "
            f"within the {policy.window_seconds}-second event window."
        )

    association = IncidentAlert(
        incident_id=incident.id, alert_id=alert.id, correlation_reason=reason,
        observed_at=observed_at, created_at=now,
    )
    db.add(association)
    db.flush()
    return association
