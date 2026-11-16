"""Store validated match-level player statistics without replacing legacy totals."""
from alembic import op
import sqlalchemy as sa
revision='20261116_0009'
down_revision='20261116_0008'
branch_labels=depends_on=None


def upgrade():
    columns=[sa.Column('id',sa.Integer(),sa.Identity(),primary_key=True),sa.Column('match_id',sa.Integer(),nullable=False),sa.Column('player_id',sa.Integer(),nullable=False)]
    for name in ('minutes_played','goals','assists'): columns.append(sa.Column(name,sa.Integer(),nullable=False))
    for name in ('shots','passes_attempted','passes_completed','tackles','progressive_passes','progressive_carries'): columns.append(sa.Column(name,sa.Integer()))
    op.create_table('player_match_stats',*columns,sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.UniqueConstraint('player_id','match_id',name='uq_player_match_stats'),
        sa.ForeignKeyConstraint(['match_id','player_id'],['match_participants.match_id','match_participants.player_id'],ondelete='CASCADE'),
        sa.CheckConstraint('minutes_played BETWEEN 0 AND 180 AND goals >= 0 AND assists >= 0',name='ck_match_stats_nonnegative'),
        sa.CheckConstraint('shots >= 0 AND passes_attempted >= 0 AND passes_completed >= 0 AND tackles >= 0 AND progressive_passes >= 0 AND progressive_carries >= 0',name='ck_match_stats_optional_nonnegative'),
        sa.CheckConstraint('passes_completed <= passes_attempted AND goals <= shots',name='ck_match_stats_consistency'),
        sa.CheckConstraint('minutes_played > 0 OR (goals=0 AND assists=0 AND coalesce(shots,0)=0 AND coalesce(passes_attempted,0)=0 AND coalesce(passes_completed,0)=0 AND coalesce(tackles,0)=0 AND coalesce(progressive_passes,0)=0 AND coalesce(progressive_carries,0)=0)',name='ck_match_stats_zero_minutes'))
    for column in ('match_id','player_id'): op.create_index('ix_player_match_stats_'+column,'player_match_stats',[column])


def downgrade(): op.drop_table('player_match_stats')
