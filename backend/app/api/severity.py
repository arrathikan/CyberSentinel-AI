"""Configuration for security alert score bands."""

import os

from pydantic import BaseModel, Field, model_validator


class SeverityPolicy(BaseModel):
    medium: float = Field(default=0.70, ge=0, le=1)
    high: float = Field(default=0.85, ge=0, le=1)
    critical: float = Field(default=0.95, ge=0, le=1)

    @model_validator(mode="after")
    def validate_order(self):
        if not self.medium < self.high < self.critical:
            raise ValueError("Severity thresholds must increase from medium to critical")
        return self

    @classmethod
    def from_environment(cls):
        return cls.model_validate({
            level: os.environ[name]
            for level in cls.model_fields
            if (name := f"ALERT_SEVERITY_{level.upper()}") in os.environ
        })

    def classify(self, score: float) -> str:
        if score >= self.critical:
            return "critical"
        if score >= self.high:
            return "high"
        if score >= self.medium:
            return "medium"
        return "low"
