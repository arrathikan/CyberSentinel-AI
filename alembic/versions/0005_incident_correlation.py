"""Add incident groups and alert memberships."""

import sqlalchemy as sa
from alembic import op

revision = "0005_incident_correlation"
down_revision = "0004_prediction_model_version"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("correlation_key", sa.String(64), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("status", sa.String(50), server_default="open", nullable=False),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("first_seen_at <= last_seen_at", name="ck_incident_seen_order"),
        sa.CheckConstraint(
            "status IN ('open', 'investigating', 'resolved', 'closed')",
            name="ck_incident_status",
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_incident_severity",
        ),
    )
    op.create_index(
        "ix_incidents_correlation_lookup", "incidents", ["correlation_key", "last_seen_at"]
    )
    for column in ("status", "severity", "last_seen_at"):
        op.create_index(f"ix_incidents_{column}", "incidents", [column])

    op.create_table(
        "incident_alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("incident_id", sa.Integer(), sa.ForeignKey("incidents.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("alert_id", sa.Integer(), sa.ForeignKey("security_alerts.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("correlation_reason", sa.String(250), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("alert_id", name="uq_incident_alerts_alert_id"),
    )
    op.create_index("ix_incident_alerts_incident_id", "incident_alerts", ["incident_id"])


def downgrade():
    op.drop_table("incident_alerts")
    op.drop_table("incidents")
