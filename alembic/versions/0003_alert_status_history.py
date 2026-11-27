"""Enforce one alert per prediction and add status audit history."""

import sqlalchemy as sa
from alembic import op

revision = "0003_alert_status_history"
down_revision = "0002_add_threshold"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(
        "uq_security_alerts_prediction_id", "security_alerts", ["prediction_id"]
    )
    op.create_table(
        "alert_status_changes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "alert_id", sa.Integer(),
            sa.ForeignKey("security_alerts.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("previous_status", sa.String(50), nullable=False),
        sa.Column("new_status", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_alert_status_changes_alert_id", "alert_status_changes", ["alert_id"]
    )


def downgrade():
    op.drop_table("alert_status_changes")
    op.drop_constraint(
        "uq_security_alerts_prediction_id", "security_alerts", type_="unique"
    )
