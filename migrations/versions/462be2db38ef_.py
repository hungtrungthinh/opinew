"""empty message

Revision ID: 462be2db38ef
Revises: 1fdd79528d55
Create Date: 2016-02-19 11:05:59.234732

"""

# revision identifiers, used by Alembic.
revision = '462be2db38ef'
down_revision = '1fdd79528d55'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('incoming_messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.Column('title', sa.String(), nullable=True),
    sa.Column('url', sa.String(), nullable=True),
    sa.Column('icon', sa.String(), nullable=True),
    sa.Column('icon_bg_color', sa.String(), nullable=True),
    sa.Column('shop_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['shop_id'], ['shop.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_constraint(u'order_products_order_id_fkey', 'order_products', type_='foreignkey')
    op.create_foreign_key(None, 'order_products', 'order', ['order_id'], ['id'])
    op.drop_constraint(u'review_request_for_order_id_fkey', 'review_request', type_='foreignkey')
    op.create_foreign_key(None, 'review_request', 'order', ['for_order_id'], ['id'])
    op.drop_constraint(u'task_order_id_fkey', 'task', type_='foreignkey')
    op.create_foreign_key(None, 'task', 'order', ['order_id'], ['id'])
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'task', type_='foreignkey')
    op.create_foreign_key(u'task_order_id_fkey', 'task', 'order', ['order_id'], ['id'], ondelete=u'CASCADE')
    op.drop_constraint(None, 'review_request', type_='foreignkey')
    op.create_foreign_key(u'review_request_for_order_id_fkey', 'review_request', 'order', ['for_order_id'], ['id'], ondelete=u'CASCADE')
    op.drop_constraint(None, 'order_products', type_='foreignkey')
    op.create_foreign_key(u'order_products_order_id_fkey', 'order_products', 'order', ['order_id'], ['id'], ondelete=u'CASCADE')
    op.drop_table('incoming_messages')
    ### end Alembic commands ###
