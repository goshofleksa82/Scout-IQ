"""Transactional audit capture, quality history and honest legacy timestamps."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from app.core.audit_sql import AUDIT_TABLES,TIMESTAMP_TABLES,install_audit_triggers
revision='20261116_0014'
down_revision='20261116_0013'
branch_labels=depends_on=None


def upgrade():
    for table in TIMESTAMP_TABLES:
        for name in ('created_at','updated_at'):
            # Add without a default first: existing observation dates are unknown.
            op.add_column(table,sa.Column(name,sa.DateTime(timezone=True),nullable=True))
            op.alter_column(table,name,server_default=sa.func.now())
    op.create_table('audit_logs',sa.Column('id',sa.Integer(),sa.Identity(),primary_key=True),sa.Column('actor_id',sa.Integer()),sa.Column('entity',sa.String(80),nullable=False),sa.Column('action',sa.String(10),nullable=False),sa.Column('record_key',JSONB(),nullable=False),sa.Column('before',JSONB()),sa.Column('after',JSONB()),sa.Column('changed_fields',JSONB(),nullable=False),sa.Column('source',sa.String(30),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.CheckConstraint("action IN ('create','update','delete')",name='ck_audit_action'))
    for name in ('actor_id','entity','created_at'): op.create_index('ix_audit_logs_'+name,'audit_logs',[name])
    op.create_table('data_quality_runs',sa.Column('id',sa.Integer(),sa.Identity(),primary_key=True),sa.Column('created_by_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='SET NULL')),sa.Column('summary',JSONB(),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()))
    install_audit_triggers(lambda sql:op.execute(sa.text(sql)))


def downgrade():
    for table in AUDIT_TABLES: op.execute(sa.text(f'DROP TRIGGER IF EXISTS scoutiq_audit_row ON "{table}"'))
    for table in (*TIMESTAMP_TABLES,'player_match_stats','watchlists','scouting_reports'): op.execute(sa.text(f'DROP TRIGGER IF EXISTS scoutiq_touch_row ON "{table}"'))
    op.drop_table('data_quality_runs');op.drop_table('audit_logs')
    for name in ('scoutiq_touch_updated','scoutiq_capture_audit','scoutiq_protect_audit'): op.execute(sa.text(f'DROP FUNCTION {name}()'))
    for table in reversed(TIMESTAMP_TABLES):
        op.drop_column(table,'updated_at');op.drop_column(table,'created_at')
