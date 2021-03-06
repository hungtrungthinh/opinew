"""empty message

Revision ID: 2d09e604b03a
Revises: 289a1a34f2fd
Create Date: 2015-11-30 15:28:47.008528

"""

# revision identifiers, used by Alembic.
revision = '2d09e604b03a'
down_revision = '289a1a34f2fd'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('order', sa.Column('task_eta', sa.DateTime(), nullable=True))
    op.add_column('order', sa.Column('task_id', sa.String(), nullable=True))
    op.add_column('order', sa.Column('task_status', sa.String(), nullable=True))
    op.drop_column('review_request', 'task_status')
    op.drop_column('review_request', 'task_eta')
    op.drop_column('review_request', 'task_id')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('review_request', sa.Column('task_id', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('review_request', sa.Column('task_eta', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('review_request', sa.Column('task_status', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_column('order', 'task_status')
    op.drop_column('order', 'task_id')
    op.drop_column('order', 'task_eta')
    ### end Alembic commands ###
