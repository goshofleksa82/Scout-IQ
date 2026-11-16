"""Add users without modifying players or their sequence."""
from alembic import op
import sqlalchemy as sa

revision = "20261116_0002"
down_revision = "20261116_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), server_default="viewer", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.CheckConstraint("role IN ('viewer', 'admin')", name="ck_users_valid_role"),
        sa.PrimaryKeyConstraint("id", name="users_pkey"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    # This deliberately affects users only. It removes user data, so use it
    # only when an explicit rollback of this feature is intended.
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
