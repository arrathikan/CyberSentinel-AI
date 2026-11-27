"""Store a prediction's model version when supplied by model metadata."""

import sqlalchemy as sa
from alembic import op

revision = "0004_prediction_model_version"
down_revision = "0003_alert_status_history"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("predictions", sa.Column("model_version", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("predictions", "model_version")
