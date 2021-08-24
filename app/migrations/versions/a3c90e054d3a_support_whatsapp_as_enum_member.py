"""support whatsapp as enum member

Revision ID: a3c90e054d3a
Revises: 3dad84c99218
Create Date: 2021-08-24 05:28:52.434323

"""
from alembic import op
import sqlalchemy as sa

# Cribbed from https://markrailton.com/blog/creating-migrations-when-changing-an-enum-in-python-using-sql-alchemy

# revision identifiers, used by Alembic.
revision = "a3c90e054d3a"
down_revision = "3dad84c99218"
branch_labels = None
depends_on = None

# Enum 'type' for PostgreSQL
enum_name = "clientidentifiertype"
# Set temporary enum 'type' for PostgreSQL
tmp_enum_name = "tmp_" + enum_name

# Options for Enum
old_options = ("PHONE_NUMBER", "IP")
new_options = sorted(old_options + ("WHATSAPP",))

# Create enum fields
old_type = sa.Enum(*old_options, name=enum_name)
new_type = sa.Enum(*new_options, name=enum_name)


def upgrade():
    # Rename current enum type to tmp_
    op.execute("ALTER TYPE " + enum_name + " RENAME TO " + tmp_enum_name)
    # Create new enum type in db
    new_type.create(op.get_bind())
    # Update column to use new enum type
    op.execute(
        "ALTER TABLE clients ALTER COLUMN type_code TYPE "
        + enum_name
        + " USING type_code::text::"
        + enum_name
    )
    # Drop old enum type
    op.execute("DROP TYPE " + tmp_enum_name)


def downgrade():
    # Instantiate db query
    op.execute(
        "DELETE FROM events WHERE client_id IN (SELECT id FROM clients WHERE type_code = 'WHATSAPP')"
    )
    op.execute("DELETE FROM clients WHERE type_code = 'WHATSAPP'")
    # Rename enum type to tmp_
    op.execute("ALTER TYPE " + enum_name + " RENAME TO " + tmp_enum_name)
    # Create enum type using old values
    old_type.create(op.get_bind())
    # Set enum type as type for event_type column
    op.execute(
        "ALTER TABLE clients ALTER COLUMN type_code TYPE "
        + enum_name
        + " USING type_code::text::"
        + enum_name
    )
    # Drop temp enum type
    op.execute("DROP TYPE " + tmp_enum_name)
