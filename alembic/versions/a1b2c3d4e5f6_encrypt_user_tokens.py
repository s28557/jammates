"""encrypt user tokens at rest

Revision ID: a1b2c3d4e5f6
Revises: 2c3d9a1e7b42
Create Date: 2026-06-11

"""
from alembic import op
import sqlalchemy as sa
from cryptography.fernet import Fernet
from app.core.config import settings

revision = 'a1b2c3d4e5f6'
down_revision = '2c3d9a1e7b42'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # widen columns to fit Fernet-encrypted output (original 500 → 1000)
    bind.execute(sa.text("ALTER TABLE users ALTER COLUMN access_token TYPE VARCHAR(1000)"))
    bind.execute(sa.text("ALTER TABLE users ALTER COLUMN refresh_token TYPE VARCHAR(1000)"))

    fernet = Fernet(settings.ENCRYPTION_KEY.encode())

    rows = bind.execute(sa.text("SELECT id, access_token, refresh_token FROM users")).fetchall()
    for row in rows:
        encrypted_access = fernet.encrypt(row.access_token.encode()).decode()
        encrypted_refresh = fernet.encrypt(row.refresh_token.encode()).decode()
        bind.execute(
            sa.text("UPDATE users SET access_token = :at, refresh_token = :rt WHERE id = :id"),
            {"at": encrypted_access, "rt": encrypted_refresh, "id": row.id},
        )


def downgrade() -> None:
    bind = op.get_bind()

    fernet = Fernet(settings.ENCRYPTION_KEY.encode())

    rows = bind.execute(sa.text("SELECT id, access_token, refresh_token FROM users")).fetchall()
    for row in rows:
        plain_access = fernet.decrypt(row.access_token.encode()).decode()
        plain_refresh = fernet.decrypt(row.refresh_token.encode()).decode()
        bind.execute(
            sa.text("UPDATE users SET access_token = :at, refresh_token = :rt WHERE id = :id"),
            {"at": plain_access, "rt": plain_refresh, "id": row.id},
        )

    bind.execute(sa.text("ALTER TABLE users ALTER COLUMN access_token TYPE VARCHAR(500)"))
    bind.execute(sa.text("ALTER TABLE users ALTER COLUMN refresh_token TYPE VARCHAR(500)"))