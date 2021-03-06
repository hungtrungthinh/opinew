"""empty message

Revision ID: 55d5b90482a4
Revises: 26d55293083e
Create Date: 2016-01-15 20:20:24.947391

"""

# revision identifiers, used by Alembic.
revision = '55d5b90482a4'
down_revision = '26d55293083e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('order', sa.Column('browser_ip', sa.String(), nullable=True))
    op.drop_column('order', 'from_browser_ip')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('order', sa.Column('from_browser_ip', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_column('order', 'browser_ip')
    ### end Alembic commands ###
