"""empty message

Revision ID: 407f3004be4e
Revises: 462be2db38ef
Create Date: 2016-02-19 11:33:05.251441

"""

# revision identifiers, used by Alembic.
revision = '407f3004be4e'
down_revision = '462be2db38ef'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('next_action',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.Column('identifier', sa.String(), nullable=True),
    sa.Column('title', sa.String(), nullable=True),
    sa.Column('url', sa.String(), nullable=True),
    sa.Column('icon', sa.String(), nullable=True),
    sa.Column('icon_bg_color', sa.String(), nullable=True),
    sa.Column('shop_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['shop_id'], ['shop.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_table('incoming_messages')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('incoming_messages',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('timestamp', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('title', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('url', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('icon', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('icon_bg_color', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('shop_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['shop_id'], [u'shop.id'], name=u'incoming_messages_shop_id_fkey'),
    sa.PrimaryKeyConstraint('id', name=u'incoming_messages_pkey')
    )
    op.drop_table('next_action')
    ### end Alembic commands ###
