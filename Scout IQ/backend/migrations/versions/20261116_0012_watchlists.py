"""Private per-user watchlists; existing players remain untouched."""
from alembic import op
import sqlalchemy as sa
revision='20261116_0012'
down_revision='20261116_0011'
branch_labels=depends_on=None


def upgrade():
    op.create_table('watchlists',sa.Column('id',sa.Integer(),sa.Identity(),primary_key=True),sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),sa.Column('name',sa.String(100),nullable=False),sa.Column('description',sa.String(1000),nullable=False,server_default=''),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.CheckConstraint('length(trim(name)) > 0',name='ck_watchlist_name'))
    op.create_index('ix_watchlists_user_id','watchlists',['user_id'])
    op.create_index('uq_watchlist_owner_name','watchlists',['user_id',sa.text('lower(name)')],unique=True)
    op.create_table('watchlist_items',sa.Column('watchlist_id',sa.Integer(),sa.ForeignKey('watchlists.id',ondelete='CASCADE'),primary_key=True),sa.Column('player_id',sa.Integer(),sa.ForeignKey('players.id',ondelete='RESTRICT'),primary_key=True),sa.Column('added_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()))
    op.create_index('ix_watchlist_items_player_id','watchlist_items',['player_id'])


def downgrade():
    op.drop_table('watchlist_items');op.drop_table('watchlists')
