"""empty message

Revision ID: 0a61dd30b5c8
Revises: 549a2225b9a3
Create Date: 2020-05-14 19:43:12.706817

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0a61dd30b5c8'
down_revision = '549a2225b9a3'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('webhook_subscription', sa.Column('secret', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('webhook_subscription', 'secret')
    # ### end Alembic commands ###
