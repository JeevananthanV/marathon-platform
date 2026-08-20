"""add_lead_status_to_participants

Revision ID: a3c4e5f6g7h8
Revises: 9268e2d6aec2
Create Date: 2026-08-19 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c4e5f6g7h8'
down_revision: Union[str, Sequence[str], None] = '9268e2d6aec2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('participants', sa.Column('lead_status', sa.String(length=30), server_default='NEW', nullable=False))
    op.create_index(op.f('ix_participants_lead_status'), 'participants', ['lead_status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_participants_lead_status'), table_name='participants')
    op.drop_column('participants', 'lead_status')
