"""Opt-in feature events, onboarding and structured beta feedback."""
from alembic import op
import sqlalchemy as sa
from app.core.audit_sql import install_audit_triggers
revision='20261116_0015'
down_revision='20261116_0014'
branch_labels=depends_on=None


def upgrade():
    op.add_column('users',sa.Column('analytics_opt_in',sa.Boolean(),nullable=False,server_default=sa.false()))
    op.add_column('users',sa.Column('onboarding_completed_at',sa.DateTime(timezone=True)))
    op.create_table('product_events',sa.Column('id',sa.Integer(),sa.Identity(),primary_key=True),sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),sa.Column('event',sa.String(40),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.CheckConstraint("event IN ('onboarding_completed','player_profile_viewed','comparison_opened','watchlist_created','report_created','report_updated','feedback_submitted')",name='ck_product_event_name'))
    for name in ['user_id','event','created_at']: op.create_index('ix_product_events_'+name,'product_events',[name])
    op.create_table('beta_feedback',sa.Column('id',sa.Integer(),sa.Identity(),primary_key=True),sa.Column('author_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),sa.Column('category',sa.String(20),nullable=False),sa.Column('area',sa.String(20),nullable=False),sa.Column('rating',sa.Integer(),nullable=False),sa.Column('message',sa.Text(),nullable=False),sa.Column('follow_up',sa.Boolean(),nullable=False,server_default=sa.false()),sa.Column('status',sa.String(20),nullable=False,server_default='new'),sa.Column('priority',sa.String(10),nullable=False,server_default='medium'),sa.Column('admin_note',sa.Text(),nullable=False,server_default=''),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.CheckConstraint("category IN ('bug','usability','data','feature')",name='ck_feedback_category'),sa.CheckConstraint("area IN ('onboarding','search','profile','comparison','watchlist','report','other')",name='ck_feedback_area'),sa.CheckConstraint('rating BETWEEN 1 AND 5',name='ck_feedback_rating'),sa.CheckConstraint("status IN ('new','triaged','planned','done','wont_do')",name='ck_feedback_status'),sa.CheckConstraint("priority IN ('low','medium','high','urgent')",name='ck_feedback_priority'))
    op.create_index('ix_beta_feedback_author_id','beta_feedback',['author_id'])
    install_audit_triggers(lambda sql:op.execute(sa.text(sql)),include_beta=True)


def downgrade():
    op.drop_table('beta_feedback');op.drop_table('product_events');op.drop_column('users','onboarding_completed_at');op.drop_column('users','analytics_opt_in')
