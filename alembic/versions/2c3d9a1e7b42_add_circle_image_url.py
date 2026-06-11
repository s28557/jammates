"""add circle image url

Revision ID: 2c3d9a1e7b42
Revises: b4f04898ea2b
Create Date: 2026-06-11 19:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2c3d9a1e7b42"
down_revision: Union[str, Sequence[str], None] = "b4f04898ea2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("circles", sa.Column("image_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("circles", "image_url")
