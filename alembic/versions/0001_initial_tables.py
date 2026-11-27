"""Initial database tables: predictions and security_alerts

Revision ID: 0001_initial_tables
Revises: 
Create Date: 2026-11-27 18:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001_initial_tables'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create predictions table
    op.create_table(
        'predictions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('prediction', sa.Integer(), nullable=False),
        sa.Column('attack_score', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_predictions_id'), 'predictions', ['id'], unique=False)
    op.create_index(op.f('ix_predictions_model_name'), 'predictions', ['model_name'], unique=False)
    op.create_index(op.f('ix_predictions_created_at'), 'predictions', ['created_at'], unique=False)

    # 2. Create security_alerts table
    op.create_table(
        'security_alerts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('prediction_id', sa.Integer(), nullable=False),
        sa.Column('severity', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='open', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['prediction_id'], ['predictions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name='check_valid_severity'
        ),
        sa.CheckConstraint(
            "status IN ('open', 'investigating', 'resolved', 'closed', 'OPEN', 'INVESTIGATING', 'RESOLVED', 'CLOSED')",
            name='check_valid_status'
        )
    )
    op.create_index(op.f('ix_security_alerts_id'), 'security_alerts', ['id'], unique=False)
    op.create_index(op.f('ix_security_alerts_prediction_id'), 'security_alerts', ['prediction_id'], unique=False)
    op.create_index(op.f('ix_security_alerts_severity'), 'security_alerts', ['severity'], unique=False)
    op.create_index(op.f('ix_security_alerts_status'), 'security_alerts', ['status'], unique=False)
    op.create_index(op.f('ix_security_alerts_created_at'), 'security_alerts', ['created_at'], unique=False)
    op.create_index('ix_alerts_severity_status', 'security_alerts', ['severity', 'status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_alerts_severity_status', table_name='security_alerts')
    op.drop_index(op.f('ix_security_alerts_created_at'), table_name='security_alerts')
    op.drop_index(op.f('ix_security_alerts_status'), table_name='security_alerts')
    op.drop_index(op.f('ix_security_alerts_severity'), table_name='security_alerts')
    op.drop_index(op.f('ix_security_alerts_prediction_id'), table_name='security_alerts')
    op.drop_index(op.f('ix_security_alerts_id'), table_name='security_alerts')
    op.drop_table('security_alerts')

    op.drop_index(op.f('ix_predictions_created_at'), table_name='predictions')
    op.drop_index(op.f('ix_predictions_model_name'), table_name='predictions')
    op.drop_index(op.f('ix_predictions_id'), table_name='predictions')
    op.drop_table('predictions')
