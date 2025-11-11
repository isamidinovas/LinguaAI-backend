"""Add language_id to flashcards safely

Revision ID: 3b32b42c86a6
Revises: 26d8593a1fd9
Create Date: 2025-11-11 15:34:34.074340

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3b32b42c86a6'
down_revision: Union[str, Sequence[str], None] = '26d8593a1fd9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
