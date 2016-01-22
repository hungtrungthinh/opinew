"""empty message

Revision ID: 26d55293083e
Revises: 434989102fbf
Create Date: 2016-01-15 17:50:08.231811

"""

# revision identifiers, used by Alembic.
revision = '26d55293083e'
down_revision = '434989102fbf'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('funnel_stream',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('shop_id', sa.Integer(), nullable=True),
    sa.Column('product_id', sa.Integer(), nullable=True),
    sa.Column('plugin_load_ts', sa.DateTime(), nullable=True),
    sa.Column('plugin_loaded_from_ip', sa.String(), nullable=True),
    sa.Column('plugin_glimpsed_ts', sa.DateTime(), nullable=True),
    sa.Column('plugin_fully_seen_ts', sa.DateTime(), nullable=True),
    sa.Column('plugin_mouse_hover_ts', sa.DateTime(), nullable=True),
    sa.Column('plugin_mouse_scroll_ts', sa.DateTime(), nullable=True),
    sa.Column('plugin_mouse_click_ts', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['product_id'], ['product.id'], ),
    sa.ForeignKeyConstraint(['shop_id'], ['shop.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column(u'order', sa.Column('from_browser_ip', sa.String(), nullable=True))
    op.add_column(u'order', sa.Column('funnel_stream_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'order', 'funnel_stream', ['funnel_stream_id'], ['id'])
    op.add_column(u'review', sa.Column('funnel_stream_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'review', 'funnel_stream', ['funnel_stream_id'], ['id'])
    op.add_column(u'review_request', sa.Column('funnel_stream_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'review_request', 'funnel_stream', ['funnel_stream_id'], ['id'])
    op.add_column(u'sent_email', sa.Column('funnel_stream_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'sent_email', 'funnel_stream', ['funnel_stream_id'], ['id'])
    op.add_column(u'task', sa.Column('funnel_stream_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'task', 'funnel_stream', ['funnel_stream_id'], ['id'])
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'task', type_='foreignkey')
    op.drop_column(u'task', 'funnel_stream_id')
    op.drop_constraint(None, 'sent_email', type_='foreignkey')
    op.drop_column(u'sent_email', 'funnel_stream_id')
    op.drop_constraint(None, 'review_request', type_='foreignkey')
    op.drop_column(u'review_request', 'funnel_stream_id')
    op.drop_constraint(None, 'review', type_='foreignkey')
    op.drop_column(u'review', 'funnel_stream_id')
    op.drop_constraint(None, 'order', type_='foreignkey')
    op.drop_column(u'order', 'funnel_stream_id')
    op.drop_column(u'order', 'from_browser_ip')
    op.drop_table('funnel_stream')
    ### end Alembic commands ###