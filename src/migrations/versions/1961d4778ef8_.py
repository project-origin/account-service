"""empty message

Revision ID: 1961d4778ef8
Revises: d3f593e661a8
Create Date: 2020-06-30 13:10:11.041138

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
from sqlalchemy.dialects import postgresql

revision = '1961d4778ef8'
down_revision = 'd3f593e661a8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    meteringpointtype = postgresql.ENUM('PRODUCTION', 'CONSUMPTION', name='meteringpointtype')
    meteringpointtype.create(op.get_bind())

    op.add_column('accounts_meteringpoint', sa.Column('type', sa.Enum('PRODUCTION', 'CONSUMPTION', name='meteringpointtype'), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('accounts_meteringpoint', 'type')
    # ### end Alembic commands ###
