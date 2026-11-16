"""Track import provenance and stable identities without overwriting existing rows."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision='20261116_0010'
down_revision='20261116_0009'
branch_labels=depends_on=None


def upgrade():
    op.create_table('import_batches',sa.Column('id',sa.Integer(),sa.Identity(),primary_key=True),
        sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('kind',sa.String(20),nullable=False),sa.Column('source',sa.String(255),nullable=False),
        sa.Column('rights_basis',sa.String(255),nullable=False),sa.Column('status',sa.String(20),nullable=False),
        sa.Column('report',JSONB(),nullable=False,server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('complete','rejected','failed')",name='ck_import_batch_status'))
    op.create_index('ix_import_batches_user_id','import_batches',['user_id'])
    op.create_table('import_identities',sa.Column('id',sa.Integer(),sa.Identity(),primary_key=True),
        sa.Column('source',sa.String(255),nullable=False),sa.Column('kind',sa.String(20),nullable=False),
        sa.Column('external_id',sa.String(128),nullable=False),sa.Column('record_id',sa.Integer(),nullable=False),
        sa.Column('fingerprint',sa.String(64),nullable=False),sa.Column('batch_id',sa.Integer(),sa.ForeignKey('import_batches.id',ondelete='RESTRICT'),nullable=False),
        sa.UniqueConstraint('source','kind','external_id',name='uq_import_external_identity'))
    op.create_index('ix_import_identities_batch_id','import_identities',['batch_id'])
    for table in ('players','matches','player_match_stats'):
        op.add_column(table,sa.Column('import_batch_id',sa.Integer()))
        op.create_foreign_key(table+'_import_batch_id_fkey',table,'import_batches',['import_batch_id'],['id'],ondelete='RESTRICT')


def downgrade():
    for table in ('players','matches','player_match_stats'):
        op.drop_constraint(table+'_import_batch_id_fkey',table,type_='foreignkey')
        op.drop_column(table,'import_batch_id')
    op.drop_table('import_identities')
    op.drop_table('import_batches')
