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
    prediction: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    attack_score: Mapped[float] = mapped_column(
        Float,
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

    def to_dict(self) -> dict[str, Any]:
        """Convert model instance to standard dictionary."""
        return {
            "id": self.id,
            "model_name": self.model_name,
            "prediction": self.prediction,
            "attack_score": self.attack_score,
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
