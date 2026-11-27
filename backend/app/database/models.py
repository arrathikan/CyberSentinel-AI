"""
CyberAgent AI - SQLAlchemy ORM Models.

Defines:
- Prediction: Stores inference outcomes, predicted labels, and attack scores.
- SecurityAlert: Stores alerts triggered by high-risk prediction events.
"""

from datetime import datetime, timezone
from typing import Any, List

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.session import Base


class Prediction(Base):
    """
    Records machine learning inference results on network flows.
    """
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    model_version: Mapped[str | None] = mapped_column(Text)
    prediction: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    attack_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    threshold: Mapped[float] = mapped_column(
        Float,
        default=0.5,
        server_default="0.5",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # 1-to-many relationship with cascading delete
    alerts: Mapped[List["SecurityAlert"]] = relationship(
        "SecurityAlert",
        back_populates="prediction",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def label(self) -> str:
        return "Attack" if self.prediction else "Benign"

    def to_dict(self) -> dict[str, Any]:
        """Convert model instance to standard dictionary."""
        return {
            "id": self.id,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "label": self.label,
            "prediction": self.prediction,
            "attack_score": self.attack_score,
            "threshold": self.threshold,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return (
            f"<Prediction(id={self.id}, model='{self.model_name}', "
            f"pred={self.prediction}, score={self.attack_score:.4f})>"
        )


class SecurityAlert(Base):
    """
    Represents a detected security threat or alert linked to a prediction.
    """
    __tablename__ = "security_alerts"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )
    prediction_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("predictions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    severity: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="open",
        server_default="open",
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Many-to-1 relationship with Prediction
    prediction: Mapped["Prediction"] = relationship(
        "Prediction",
        back_populates="alerts",
    )

    __table_args__ = (
        UniqueConstraint("prediction_id", name="uq_security_alerts_prediction_id"),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="check_valid_severity",
        ),
        CheckConstraint(
            "status IN ('open', 'investigating', 'resolved', 'closed', 'OPEN', 'INVESTIGATING', 'RESOLVED', 'CLOSED')",
            name="check_valid_status",
        ),
        Index("ix_alerts_severity_status", "severity", "status"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert model instance to standard dictionary."""
        return {
            "id": self.id,
            "prediction_id": self.prediction_id,
            "severity": self.severity,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return (
            f"<SecurityAlert(id={self.id}, prediction_id={self.prediction_id}, "
            f"severity='{self.severity}', status='{self.status}')>"
        )


class AlertStatusChange(Base):
    """Audit record for a committed alert status transition."""

    __tablename__ = "alert_status_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[int] = mapped_column(
        ForeignKey("security_alerts.id", ondelete="CASCADE"), index=True,
    )
    previous_status: Mapped[str] = mapped_column(String(50))
    new_status: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )


class Incident(Base):
    """Group of detection alerts with the same pseudonymous flow key."""

    __tablename__ = "incidents"
    __table_args__ = (
        Index("ix_incidents_correlation_lookup", "correlation_key", "last_seen_at"),
        CheckConstraint("first_seen_at <= last_seen_at", name="ck_incident_seen_order"),
        CheckConstraint(
            "status IN ('open', 'investigating', 'resolved', 'closed')",
            name="ck_incident_status",
        ),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_incident_severity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    correlation_key: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(50), server_default="open", index=True)
    severity: Mapped[str] = mapped_column(String(50), index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IncidentAlert(Base):
    """One incident association per original alert."""

    __tablename__ = "incident_alerts"
    __table_args__ = (
        UniqueConstraint("alert_id", name="uq_incident_alerts_alert_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), index=True,
    )
    alert_id: Mapped[int] = mapped_column(ForeignKey("security_alerts.id", ondelete="CASCADE"))
    correlation_reason: Mapped[str] = mapped_column(String(250))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
