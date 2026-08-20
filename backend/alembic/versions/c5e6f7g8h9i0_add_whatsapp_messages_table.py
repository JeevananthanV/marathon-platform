"""add_whatsapp_messages_table

Revision ID: c5e6f7g8h9i0
Revises: b4d5f6g7h8i9
Create Date: 2026-08-19 14:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5e6f7g8h9i0'
down_revision: Union[str, Sequence[str], None] = 'b4d5f6g7h8i9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add whatsapp_messages table and participant whatsapp_consent."""
    op.add_column('participants', sa.Column('whatsapp_consent', sa.Boolean(), server_default='1', nullable=False))
    
    op.create_table(
        'whatsapp_messages',
        sa.Column('id', sa.String(length=36), primary_key=True, nullable=False),
        sa.Column('registration_id', sa.String(length=36), sa.ForeignKey('registrations.id', ondelete='CASCADE'), nullable=True),
        sa.Column('participant_id', sa.String(length=36), sa.ForeignKey('participants.id', ondelete='CASCADE'), nullable=True),
        sa.Column('phone_number', sa.String(length=30), nullable=False),
        sa.Column('message_type', sa.String(length=50), nullable=False),
        sa.Column('template_name', sa.String(length=100), nullable=False),
        sa.Column('message_content', sa.Text(), nullable=True),
        sa.Column('provider', sa.String(length=30), server_default='MOCK', nullable=False),
        sa.Column('provider_message_id', sa.String(length=150), nullable=True),
        sa.Column('idempotency_key', sa.String(length=150), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='PENDING', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.String(length=500), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default='0', nullable=False),
    )
    op.create_index(op.f('ix_whatsapp_messages_registration_id'), 'whatsapp_messages', ['registration_id'], unique=False)
    op.create_index(op.f('ix_whatsapp_messages_participant_id'), 'whatsapp_messages', ['participant_id'], unique=False)
    op.create_index(op.f('ix_whatsapp_messages_phone_number'), 'whatsapp_messages', ['phone_number'], unique=False)
    op.create_index(op.f('ix_whatsapp_messages_message_type'), 'whatsapp_messages', ['message_type'], unique=False)
    op.create_index(op.f('ix_whatsapp_messages_provider_message_id'), 'whatsapp_messages', ['provider_message_id'], unique=False)
    op.create_index(op.f('ix_whatsapp_messages_idempotency_key'), 'whatsapp_messages', ['idempotency_key'], unique=True)
    op.create_index(op.f('ix_whatsapp_messages_status'), 'whatsapp_messages', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_whatsapp_messages_status'), table_name='whatsapp_messages')
    op.drop_index(op.f('ix_whatsapp_messages_idempotency_key'), table_name='whatsapp_messages')
    op.drop_index(op.f('ix_whatsapp_messages_provider_message_id'), table_name='whatsapp_messages')
    op.drop_index(op.f('ix_whatsapp_messages_message_type'), table_name='whatsapp_messages')
    op.drop_index(op.f('ix_whatsapp_messages_phone_number'), table_name='whatsapp_messages')
    op.drop_index(op.f('ix_whatsapp_messages_participant_id'), table_name='whatsapp_messages')
    op.drop_index(op.f('ix_whatsapp_messages_registration_id'), table_name='whatsapp_messages')
    op.drop_table('whatsapp_messages')
    op.drop_column('participants', 'whatsapp_consent')
