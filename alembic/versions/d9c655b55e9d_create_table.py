"""Create table

Revision ID: d9c655b55e9d
Revises: d4b6e20424ba
Create Date: 2026-03-30 11:25:31.105180

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9c655b55e9d'
down_revision: Union[str, Sequence[str], None] = 'd4b6e20424ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем колонки с проверкой IF NOT EXISTS
    conn = op.get_bind()
    
    # Проверяем, существует ли колонка first_name
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'idempotency_keys' AND column_name = 'first_name'
    """))
    if not result.fetchone():
        op.add_column('idempotency_keys', sa.Column('first_name', sa.String(), nullable=True))
    
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'idempotency_keys' AND column_name = 'last_name'
    """))
    if not result.fetchone():
        op.add_column('idempotency_keys', sa.Column('last_name', sa.String(), nullable=True))
    
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'idempotency_keys' AND column_name = 'email'
    """))
    if not result.fetchone():
        op.add_column('idempotency_keys', sa.Column('email', sa.String(), nullable=True))
    
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'idempotency_keys' AND column_name = 'seat'
    """))
    if not result.fetchone():
        op.add_column('idempotency_keys', sa.Column('seat', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('idempotency_keys', 'seat')
    op.drop_column('idempotency_keys', 'email')
    op.drop_column('idempotency_keys', 'last_name')
    op.drop_column('idempotency_keys', 'first_name')
