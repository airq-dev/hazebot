"""metrics table

Revision ID: 3dad84c99218
Revises: 7de8a31a8e57
Create Date: 2021-08-19 06:27:37.149813

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3dad84c99218"
down_revision = "7de8a31a8e57"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("zipcode_id", sa.Integer(), nullable=False),
        sa.Column("pm25", sa.Float(), nullable=False),
        sa.Column("humidity", sa.Float(), nullable=False),
        sa.Column("pm_cf_1", sa.Float(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["zipcode_id"], ["zipcodes.id"], name="metrics_zipcode_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_metrics_created_at"), "metrics", ["created_at"], unique=False
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_metrics_created_at"), table_name="metrics")
    op.drop_table("metrics")
    # ### end Alembic commands ###