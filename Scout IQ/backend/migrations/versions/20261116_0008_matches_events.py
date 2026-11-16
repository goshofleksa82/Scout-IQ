"""Create matches, evidenced participants, and goal/card events."""
from alembic import op
import sqlalchemy as sa
revision = '20261116_0008'
down_revision = '20261116_0007'
branch_labels = depends_on = None


def upgrade():
    op.create_table('matches',sa.Column('id',sa.Integer(),sa.Identity(),primary_key=True),
        sa.Column('home_club_id',sa.Integer(),sa.ForeignKey('clubs.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('away_club_id',sa.Integer(),sa.ForeignKey('clubs.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('competition_id',sa.Integer(),sa.ForeignKey('competitions.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('season_id',sa.Integer(),sa.ForeignKey('seasons.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('kickoff_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('duration_minutes',sa.Integer(),nullable=False,server_default='90'),
        sa.Column('status',sa.String(20),nullable=False,server_default='scheduled'),
        sa.CheckConstraint('home_club_id <> away_club_id',name='ck_match_distinct_clubs'),
        sa.CheckConstraint('duration_minutes BETWEEN 1 AND 150',name='ck_match_duration'),
        sa.CheckConstraint("status IN ('scheduled','live','finished')",name='ck_match_status'))
    for column in ('competition_id','season_id','kickoff_at'): op.create_index('ix_matches_'+column,'matches',[column])
    op.create_table('match_participants',
        sa.Column('match_id',sa.Integer(),sa.ForeignKey('matches.id',ondelete='CASCADE'),primary_key=True),
        sa.Column('player_id',sa.Integer(),sa.ForeignKey('players.id',ondelete='RESTRICT'),primary_key=True),
        sa.Column('club_id',sa.Integer(),sa.ForeignKey('clubs.id',ondelete='RESTRICT'),nullable=False))
    op.create_table('match_events',sa.Column('id',sa.Integer(),sa.Identity(),primary_key=True),
        sa.Column('match_id',sa.Integer(),nullable=False),sa.Column('player_id',sa.Integer(),nullable=False),
        sa.Column('event_type',sa.String(20),nullable=False),sa.Column('minute',sa.Integer(),nullable=False),
        sa.Column('added_time',sa.Integer(),nullable=False,server_default='0'),
        sa.Column('related_goal_id',sa.Integer(),sa.ForeignKey('match_events.id',ondelete='RESTRICT'),unique=True),
        sa.ForeignKeyConstraint(['match_id','player_id'],['match_participants.match_id','match_participants.player_id'],ondelete='CASCADE'),
        sa.CheckConstraint("event_type IN ('goal','assist','yellow_card','red_card')",name='ck_event_type'),
        sa.CheckConstraint('minute BETWEEN 0 AND 150 AND added_time BETWEEN 0 AND 30',name='ck_event_time'))
    for column in ('match_id','player_id'): op.create_index('ix_match_events_'+column,'match_events',[column])


def downgrade():
    op.drop_table('match_events')
    op.drop_table('match_participants')
    op.drop_table('matches')
