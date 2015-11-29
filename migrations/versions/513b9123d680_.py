"""empty message

Revision ID: 513b9123d680
Revises: 299c5b2c28ac
Create Date: 2015-11-22 17:21:01.906204

"""

# revision identifiers, used by Alembic.
revision = '513b9123d680'
down_revision = '299c5b2c28ac'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('review_report',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('action', sa.Integer(), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('review_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['review_id'], ['review.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('review_report')
    ### end Alembic commands ###