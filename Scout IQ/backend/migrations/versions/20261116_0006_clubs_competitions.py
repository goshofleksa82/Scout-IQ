"""Introduce relational clubs; backfill existing players without changing totals."""
from alembic import op
import sqlalchemy as sa
revision = "20261116_0006"
down_revision = "20261116_0005"
branch_labels = depends_on = None


def upgrade():
    op.create_table('competitions', sa.Column('id', sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False), sa.Column('country', sa.String(100)),
        sa.CheckConstraint('length(trim(name)) > 0', name='ck_competitions_name'))
    op.create_table('clubs', sa.Column('id', sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False), sa.Column('country', sa.String(100)),
        sa.Column('competition_id', sa.Integer(), sa.ForeignKey('competitions.id', ondelete='RESTRICT')),
        sa.CheckConstraint('length(trim(name)) > 0', name='ck_clubs_name'))
    op.create_index('uq_competitions_name_country', 'competitions', [sa.text('lower(name)'), sa.text("lower(coalesce(country, ''))")], unique=True)
    op.create_index('uq_clubs_name_country', 'clubs', [sa.text('lower(name)'), sa.text("lower(coalesce(country, ''))")], unique=True)
    op.create_index('ix_clubs_competition_id', 'clubs', ['competition_id'])
    op.add_column('players', sa.Column('club_id', sa.Integer(), nullable=True))
    op.create_foreign_key('players_club_id_fkey', 'players', 'clubs', ['club_id'], ['id'], ondelete='RESTRICT')
    op.execute('INSERT INTO clubs (name) SELECT min(trim(club)) FROM players GROUP BY lower(trim(club))')
    op.execute('UPDATE players p SET club_id = c.id FROM clubs c WHERE lower(trim(p.club)) = lower(c.name) AND c.country IS NULL')
    op.alter_column('players', 'club_id', nullable=False)
    op.create_index('ix_players_club_id', 'players', ['club_id'])


def downgrade():
    op.drop_index('ix_players_club_id', table_name='players')
    op.drop_constraint('players_club_id_fkey', 'players', type_='foreignkey')
    op.drop_column('players', 'club_id')
    op.drop_table('clubs')
    op.drop_table('competitions')
