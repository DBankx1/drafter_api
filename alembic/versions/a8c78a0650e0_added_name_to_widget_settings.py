"""Added name to widget settings

Revision ID: a8c78a0650e0
Revises: 2f835e541b8b
Create Date: 2026-05-14 00:02:07.784680

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a8c78a0650e0'
down_revision = '2f835e541b8b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('widget_settings', sa.Column(
        'name',
        sa.String(),
        nullable=False,
        server_default='AI Assistant'
    ))

    op.alter_column('widget_settings', 'name', server_default=None)

def downgrade():
    op.drop_column('widget_settings', 'name')