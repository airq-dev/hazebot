"""remove metrics table

Revision ID: cf79e49ee709
Revises: 3dad84c99218
Create Date: 2021-08-26 06:08:39.317480

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "cf79e49ee709"
down_revision = "3dad84c99218"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("ix_metrics_created_at", table_name="metrics")
    op.drop_table("metrics")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "metrics",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("zipcode_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(
            "pm25",
            postgresql.DOUBLE_PRECISION(precision=53),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "humidity",
            postgresql.DOUBLE_PRECISION(precision=53),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "pm_cf_1",
            postgresql.DOUBLE_PRECISION(precision=53),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "details",
            postgresql.JSON(astext_type=sa.Text()),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["zipcode_id"], ["zipcodes.id"], name="metrics_zipcode_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="metrics_pkey"),
    )
    op.create_index("ix_metrics_created_at", "metrics", ["created_at"], unique=False)
    # ### end Alembic commands ###
