"""empty message

Revision ID: 32240be95484
Revises: 289a1a34f2fd
Create Date: 2015-11-29 21:24:23.196673

"""

# revision identifiers, used by Alembic.
revision = '32240be95484'
down_revision = '289a1a34f2fd'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('question',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('body', sa.String(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('about_product_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['about_product_id'], ['product.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('answer',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('body', sa.String(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('to_question_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['to_question_id'], ['question.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('answer')
    op.drop_table('question')
    ### end Alembic commands ###
