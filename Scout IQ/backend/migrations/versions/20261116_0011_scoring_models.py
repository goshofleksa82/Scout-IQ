"""Versioned, explicitly uncalibrated statistical scoring definitions."""
import json
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision='20261116_0011'
down_revision='20261116_0010'
branch_labels=depends_on=None


def upgrade():
    op.create_table('scoring_models',sa.Column('id',sa.Integer(),sa.Identity(),primary_key=True),
        sa.Column('name',sa.String(100),nullable=False),sa.Column('version',sa.String(20),nullable=False),
        sa.Column('position_group',sa.String(20),nullable=False),sa.Column('weights',JSONB(),nullable=False),
        sa.Column('description',sa.String(1000),nullable=False),sa.Column('created_by_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='SET NULL')),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.UniqueConstraint('position_group','version',name='uq_scoring_model_group_version'),
        sa.CheckConstraint("position_group IN ('strikers','wingers','midfielders','defenders','goalkeepers')",name='ck_scoring_group'),
        sa.CheckConstraint("version ~ '^(0|[1-9][0-9]{0,3})[.](0|[1-9][0-9]{0,3})[.](0|[1-9][0-9]{0,3})$'",name='ck_scoring_version'))
    defaults={
        'strikers':{'goals_per_90':0.4,'assists_per_90':0.15,'shots_per_90':0.2,'goal_conversion_pct':0.25},
        'wingers':{'goals_per_90':0.3,'assists_per_90':0.3,'shots_per_90':0.2,'progressive_actions_per_90':0.2},
        'midfielders':{'assists_per_90':0.25,'progressive_actions_per_90':0.3,'tackles_per_90':0.15,'pass_completion_pct':0.3},
        'defenders':{'tackles_per_90':0.4,'pass_completion_pct':0.25,'progressive_actions_per_90':0.2,'passes_completed_per_90':0.15},
        'goalkeepers':{'pass_completion_pct':0.6,'passes_completed_per_90':0.4},
    }
    for group,weights in defaults.items():
        # Fixed metadata, never football observations or credentials. Literal
        # SQL also supports Alembic offline output for JSONB seed definitions.
        payload=json.dumps(weights).replace("'","''")
        op.execute(sa.text("INSERT INTO scoring_models (name,version,position_group,weights,description) VALUES ('ScoutIQ statistical criteria','0.1.0','"+group+"','"+payload+"'::jsonb,'Uncalibrated configurable decision-support criteria; interpret with video and context.')"))


def downgrade(): op.drop_table('scoring_models')
