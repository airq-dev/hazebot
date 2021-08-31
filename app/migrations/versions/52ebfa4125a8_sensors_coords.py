"""sensors coords

Revision ID: 52ebfa4125a8
Revises: 5f3e5ff4f100
Create Date: 2021-08-31 00:35:45.265217

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import orm
from geoalchemy2.types import Geometry


# revision identifiers, used by Alembic.
revision = '52ebfa4125a8'
down_revision = '5f3e5ff4f100'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('sensors', sa.Column('coordinates', geoalchemy2.types.Geometry(geometry_type='POINT', from_text='ST_GeomFromEWKT', name='geometry'), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('sensors', 'coordinates')
    # ### end Alembic commands ###

    # Now populate coordinates from existing data
    from airq.lib.util import chunk_list
    from airq.models.zipcodes import Sensor

    bind = op.get_bind()
    session = orm.Session(bind=bind)

    updates = []
    for zipcode in session.query(Sensor).all():
        data = dict(
            id=zipcode.id,
            coordinates=f"POINT({zipcode.longitude} {zipcode.latitude})",
        )
        updates.append(data)

    print(f"Setting coordinates for {len(updates)} sensors")
    num_processed = 0
    for mappings in chunk_list(updates):
        session.bulk_update_mappings(Sensor, mappings)
        session.commit()
        num_processed += len(mappings)
        print(f"Processed {num_processed} sensors")