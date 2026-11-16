"""Add indexes for scouting filters without changing player rows."""
from alembic import op
import sqlalchemy as sa
revision = "20261116_0005"
down_revision = "20261116_0004"
branch_labels = depends_on = None


def upgrade():
    op.create_index("ix_players_position_club_age", "players", [sa.text("lower(position)"), sa.text("lower(club)"), "age"])
    op.create_index("ix_players_club_lower", "players", [sa.text("lower(club)")])
    for name in ("age", "goals", "assists", "minutes_played"):
        op.create_index("ix_players_" + name, "players", [name])


def downgrade():
    for name in ("position_club_age", "club_lower", "age", "goals", "assists", "minutes_played"):
        op.drop_index("ix_players_" + name, table_name="players")
