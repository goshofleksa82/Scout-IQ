"""Baseline of the existing players schema.

For an existing, verified players table, stamp this revision; do not run its
upgrade. Only a new, empty database needs the CREATE TABLE below.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261116_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("position", sa.String(10), nullable=False),
        sa.Column("club", sa.String(100), nullable=False),
        sa.Column("goals", sa.Integer(), nullable=False),
        sa.Column("assists", sa.Integer(), nullable=False),
        sa.Column("minutes_played", sa.Integer(), nullable=False),
        sa.CheckConstraint("goals >= 0", name="players_goals_check"),
        sa.CheckConstraint("assists >= 0", name="players_assists_check"),
        sa.CheckConstraint("minutes_played >= 0", name="players_minutes_played_check"),
        sa.PrimaryKeyConstraint("id", name="players_pkey"),
    )


def downgrade() -> None:
    raise RuntimeError("The players baseline cannot be downgraded: player data must be preserved")
