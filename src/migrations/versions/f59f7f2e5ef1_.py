"""empty message

Revision ID: f59f7f2e5ef1
Revises: e46a7069249a
Create Date: 2020-06-04 06:41:30.212092

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f59f7f2e5ef1'
down_revision = 'e46a7069249a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('auth_user', sa.Column('last_login', sa.DateTime(timezone=True), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('auth_user', 'last_login')
    # ### end Alembic commands ###
