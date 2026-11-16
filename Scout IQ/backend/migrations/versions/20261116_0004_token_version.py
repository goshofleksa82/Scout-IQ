"""Add account-wide access-token revocation after password changes."""
from alembic import op
import sqlalchemy as sa
revision = "20261116_0004"
down_revision = "20261116_0003"
branch_labels = depends_on = None


def upgrade():
    op.add_column("users", sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))
    op.create_check_constraint("ck_users_token_version", "users", "token_version >= 0")


def downgrade():
    op.drop_constraint("ck_users_token_version", "users", type_="check")
    op.drop_column("users", "token_version")
