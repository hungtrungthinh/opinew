"""empty message

Revision ID: 46518b348ec0
Revises: 1ce2ef8dede8
Create Date: 2016-04-07 20:40:36.283925

"""

# revision identifiers, used by Alembic.
revision = '46518b348ec0'
down_revision = '1ce2ef8dede8'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('subscription', sa.Column('trialed_for', sa.Integer(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('subscription', 'trialed_for')
    ### end Alembic commands ###
