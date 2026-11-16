"""Add hashed, rotating refresh sessions; preserve all users and players."""
from alembic import op
import sqlalchemy as sa

revision = "20261116_0003"
down_revision = "20261116_0002"
branch_labels = depends_on = None


def upgrade():
    op.create_table("refresh_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("family_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("replaced_by", sa.String(36)),
    )
    op.create_index("ix_refresh_sessions_family_id", "refresh_sessions", ["family_id"])
    op.create_index("ix_refresh_sessions_user_id", "refresh_sessions", ["user_id"])


def downgrade():
    op.drop_table("refresh_sessions")
