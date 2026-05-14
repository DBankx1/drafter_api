"""Create widget position type

Revision ID: 2f835e541b8b
Revises: be6bd62e2f78
Create Date: 2026-05-12 00:24:38.776520

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2f835e541b8b'
down_revision = 'be6bd62e2f78'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('knowledge_bases', 'kb_size',
        existing_type=sa.INTEGER(),
        nullable=True)

    widget_position = postgresql.ENUM(
        'TOP_LEFT', 'TOP_RIGHT', 'BOTTOM_LEFT', 'BOTTOM_RIGHT',
        name='widgetposition'
    )
    widget_position.create(op.get_bind())

    op.alter_column('widget_settings', 'position',
        type_=widget_position,
        postgresql_using='position::widgetposition',
        nullable=False)

def downgrade():
    op.alter_column('widget_settings', 'position',
        type_=sa.VARCHAR(),
        existing_type=postgresql.ENUM(name='widgetposition'),
        nullable=True)

    op.alter_column('knowledge_bases', 'kb_size',
        existing_type=sa.INTEGER(),
        nullable=False)

    postgresql.ENUM(name='widgetposition').drop(op.get_bind())