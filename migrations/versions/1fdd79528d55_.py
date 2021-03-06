"""empty message

Revision ID: 1fdd79528d55
Revises: 53326beb4fe7
Create Date: 2016-02-12 12:50:49.762862

"""

# revision identifiers, used by Alembic.
revision = '1fdd79528d55'
down_revision = '53326beb4fe7'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('answer', sa.Column('created_ts', sa.DateTime(), nullable=True))
    op.add_column('answer', sa.Column('question_id', sa.Integer(), nullable=True))
    op.drop_constraint(u'answer_to_question_id_fkey', 'answer', type_='foreignkey')
    op.create_foreign_key(None, 'answer', 'question', ['question_id'], ['id'])
    op.drop_column('answer', 'to_question_id')
    op.add_column('question', sa.Column('created_ts', sa.DateTime(), nullable=True))
    op.add_column('question', sa.Column('product_id', sa.Integer(), nullable=True))
    op.drop_constraint(u'question_about_product_id_fkey', 'question', type_='foreignkey')
    op.create_foreign_key(None, 'question', 'product', ['product_id'], ['id'])
    op.drop_column('question', 'about_product_id')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('question', sa.Column('about_product_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'question', type_='foreignkey')
    op.create_foreign_key(u'question_about_product_id_fkey', 'question', 'product', ['about_product_id'], ['id'])
    op.drop_column('question', 'product_id')
    op.drop_column('question', 'created_ts')
    op.add_column('answer', sa.Column('to_question_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'answer', type_='foreignkey')
    op.create_foreign_key(u'answer_to_question_id_fkey', 'answer', 'question', ['to_question_id'], ['id'])
    op.drop_column('answer', 'question_id')
    op.drop_column('answer', 'created_ts')
    ### end Alembic commands ###
