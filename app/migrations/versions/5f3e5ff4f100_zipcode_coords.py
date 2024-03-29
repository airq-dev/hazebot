"""zipcode coords

Revision ID: 5f3e5ff4f100
Revises: cf79e49ee709
Create Date: 2021-08-29 23:40:42.667984

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import orm
from geoalchemy2.types import Geometry

# revision identifiers, used by Alembic.
revision = "5f3e5ff4f100"
down_revision = "cf79e49ee709"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "zipcodes",
        sa.Column(
            "coordinates",
            Geometry(
                geometry_type="POINT", from_text="ST_GeomFromEWKT", name="geometry"
            ),
            nullable=True,
        ),
    )
    # ### end Alembic commands ###

    # Now populate coordinates from existing data
    from airq.lib.util import chunk_list
    from airq.models.zipcodes import Zipcode

    bind = op.get_bind()
    session = orm.Session(bind=bind)

    updates = []
    for zipcode in session.query(Zipcode).all():
        data = dict(
            id=zipcode.id,
            coordinates=f"POINT({zipcode.longitude} {zipcode.latitude})",
        )
        updates.append(data)

    print(f"Setting coordinates for {len(updates)} zipcodes")
    num_processed = 0
    for mappings in chunk_list(updates):
        session.bulk_update_mappings(Zipcode, mappings)
        session.commit()
        num_processed += len(mappings)
        print(f"Processed {num_processed} zipcodes")


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("zipcodes", "coordinates")
    # ### end Alembic commands ###
