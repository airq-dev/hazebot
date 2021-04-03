"""Track pm_cf_1

Revision ID: 7de8a31a8e57
Revises: bc92ae15a407
Create Date: 2021-04-03 19:52:01.178064

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7de8a31a8e57'
down_revision = 'bc92ae15a407'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('clients', sa.Column('last_pm_cf_1', sa.Float(), nullable=True))
    op.add_column('sensors', sa.Column('pm_cf_1', sa.Float(), server_default='0', nullable=False))
    op.add_column('zipcodes', sa.Column('pm_cf_1', sa.Float(), server_default='0', nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('zipcodes', 'pm_cf_1')
    op.drop_column('sensors', 'pm_cf_1')
    op.drop_column('clients', 'last_pm_cf_1')
    # ### end Alembic commands ###
