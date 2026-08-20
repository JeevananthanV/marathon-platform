"""add_zoho_sync_columns_to_registrations

Revision ID: b4d5f6g7h8i9
Revises: a3c4e5f6g7h8
Create Date: 2026-08-19 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4d5f6g7h8i9'
down_revision: Union[str, Sequence[str], None] = 'a3c4e5f6g7h8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('registrations', sa.Column('zoho_sync_status', sa.String(length=20), server_default='PENDING', nullable=False))
    op.add_column('registrations', sa.Column('zoho_last_sync_attempt', sa.DateTime(timezone=True), nullable=True))
    op.add_column('registrations', sa.Column('zoho_last_successful_sync', sa.DateTime(timezone=True), nullable=True))
    op.add_column('registrations', sa.Column('zoho_error_message', sa.String(length=500), nullable=True))
    op.add_column('registrations', sa.Column('zoho_retry_count', sa.Integer(), server_default='0', nullable=False))
    op.create_index(op.f('ix_registrations_zoho_sync_status'), 'registrations', ['zoho_sync_status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_registrations_zoho_sync_status'), table_name='registrations')
    op.drop_column('registrations', 'zoho_retry_count')
    op.drop_column('registrations', 'zoho_error_message')
    op.drop_column('registrations', 'zoho_last_successful_sync')
    op.drop_column('registrations', 'zoho_last_sync_attempt')
    op.drop_column('registrations', 'zoho_sync_status')
