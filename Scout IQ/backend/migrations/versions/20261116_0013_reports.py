"""Private structured scouting reports and immutable API revision history."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision='20261116_0013'
down_revision='20261116_0012'
branch_labels=depends_on=None


def upgrade():
    columns=[sa.Column('id',sa.Integer(),sa.Identity(),primary_key=True),sa.Column('author_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),sa.Column('player_id',sa.Integer(),sa.ForeignKey('players.id',ondelete='RESTRICT'),nullable=False),sa.Column('title',sa.String(150),nullable=False),sa.Column('observed_on',sa.Date()),sa.Column('context',sa.String(1000),nullable=False,server_default='')]
    columns.extend(sa.Column(name,sa.Text(),nullable=False,server_default='') for name in ['technical','tactical','physical','mental','summary'])
    columns.extend([sa.Column('recommendation',sa.String(20),nullable=False,server_default='observe'),sa.Column('version',sa.Integer(),nullable=False,server_default='1'),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.CheckConstraint('length(trim(title)) > 0',name='ck_report_title'),sa.CheckConstraint('version >= 1',name='ck_report_version'),sa.CheckConstraint("recommendation IN ('observe','follow_up','shortlist','not_now')",name='ck_report_recommendation')])
    op.create_table('scouting_reports',*columns)
    for name in ['author_id','player_id']: op.create_index('ix_scouting_reports_'+name,'scouting_reports',[name])
    op.create_index('ix_reports_author_player','scouting_reports',['author_id','player_id'])
    op.create_table('scouting_report_versions',sa.Column('report_id',sa.Integer(),sa.ForeignKey('scouting_reports.id',ondelete='CASCADE'),primary_key=True),sa.Column('version',sa.Integer(),primary_key=True),sa.Column('content',JSONB(),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.CheckConstraint('version >= 1',name='ck_report_history_version'))


def downgrade():
    op.drop_table('scouting_report_versions');op.drop_table('scouting_reports')
