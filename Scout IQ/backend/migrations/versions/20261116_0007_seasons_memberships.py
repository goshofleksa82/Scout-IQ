"""Add dated memberships with database-enforced overlap prevention."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ExcludeConstraint
revision = '20261116_0007'
down_revision = '20261116_0006'
branch_labels = depends_on = None


def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public')
    op.create_table('seasons', sa.Column('id',sa.Integer(),sa.Identity(),primary_key=True),
        sa.Column('name',sa.String(30),nullable=False),sa.Column('starts_on',sa.Date(),nullable=False),sa.Column('ends_on',sa.Date(),nullable=False),
        sa.CheckConstraint('ends_on >= starts_on',name='ck_seasons_dates'))
    op.create_index('uq_seasons_name','seasons',[sa.text('lower(name)')],unique=True)
    op.create_table('player_club_memberships',sa.Column('id',sa.Integer(),sa.Identity(),primary_key=True),
        sa.Column('player_id',sa.Integer(),sa.ForeignKey('players.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('club_id',sa.Integer(),sa.ForeignKey('clubs.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('previous_club_id',sa.Integer(),sa.ForeignKey('clubs.id',ondelete='RESTRICT')),
        sa.Column('season_id',sa.Integer(),sa.ForeignKey('seasons.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('joined_on',sa.Date(),nullable=False),sa.Column('left_on',sa.Date()),
        sa.CheckConstraint('left_on IS NULL OR left_on > joined_on',name='ck_membership_dates'),
        ExcludeConstraint(('player_id','='),(sa.text("daterange(joined_on, left_on, '[)')"),'&&'),name='ex_membership_overlap',using='gist'))
    for column in ('player_id','club_id','season_id'):
        op.create_index('ix_player_club_memberships_'+column,'player_club_memberships',[column])


def downgrade():
    op.drop_table('player_club_memberships')
    op.drop_table('seasons')
    # btree_gist may be shared by other tables; do not remove it.
