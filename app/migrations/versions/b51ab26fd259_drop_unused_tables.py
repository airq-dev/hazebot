"""Drop unused tables

Revision ID: b51ab26fd259
Revises: 3e4e61dc004d
Create Date: 2020-09-16 15:36:47.621338

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b51ab26fd259"
down_revision = "3e4e61dc004d"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("metrics")
    op.drop_index("ix_subscriptions_disabled_at", table_name="subscriptions")
    op.drop_index("ix_subscriptions_last_executed_at", table_name="subscriptions")
    op.drop_table("subscriptions")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "subscriptions",
        sa.Column("zipcode_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("client_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("created_at", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("disabled_at", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(
            "last_executed_at", sa.INTEGER(), autoincrement=False, nullable=False
        ),
        sa.Column(
            "last_pm25",
            postgresql.DOUBLE_PRECISION(precision=53),
            autoincrement=False,
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["client_id"], ["clients.id"], name="subscription_client_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["zipcode_id"], ["zipcodes.id"], name="subscription_zipcode_id_fkey"
        ),
        sa.PrimaryKeyConstraint("zipcode_id", "client_id", name="subscriptions_pkey"),
    )
    op.create_index(
        "ix_subscriptions_last_executed_at",
        "subscriptions",
        ["last_executed_at"],
        unique=False,
    )
    op.create_index(
        "ix_subscriptions_disabled_at", "subscriptions", ["disabled_at"], unique=False
    )
    op.create_table(
        "metrics",
        sa.Column("zipcode_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("timestamp", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(
            "value",
            postgresql.DOUBLE_PRECISION(precision=53),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("num_sensors", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(
            "max_sensor_distance",
            postgresql.DOUBLE_PRECISION(precision=53),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "min_sensor_distance",
            postgresql.DOUBLE_PRECISION(precision=53),
            autoincrement=False,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["zipcode_id"], ["zipcodes.id"], name="metrics_zipcodes_fkey"
        ),
        sa.PrimaryKeyConstraint("zipcode_id", "timestamp", name="metrics_pkey"),
    )
    # ### end Alembic commands ###
