"""empty message

Revision ID: b86b0214ee50
Revises: 1961d4778ef8
Create Date: 2020-07-22 09:04:03.216073

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b86b0214ee50'
down_revision = '1961d4778ef8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('forecast_forecast',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('public_id', sa.String(), nullable=False),
    sa.Column('created', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('begin', sa.DateTime(timezone=True), nullable=False),
    sa.Column('end', sa.DateTime(timezone=True), nullable=False),
    sa.Column('sector', sa.String(), nullable=False),
    sa.Column('reference', sa.String(), nullable=False),
    sa.Column('forecast', postgresql.ARRAY(sa.Integer()), nullable=False),
    sa.Column('resolution', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('recipient_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['recipient_id'], ['auth_user.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['auth_user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_forecast_forecast_begin'), 'forecast_forecast', ['begin'], unique=False)
    op.create_index(op.f('ix_forecast_forecast_end'), 'forecast_forecast', ['end'], unique=False)
    op.create_index(op.f('ix_forecast_forecast_id'), 'forecast_forecast', ['id'], unique=False)
    op.create_index(op.f('ix_forecast_forecast_public_id'), 'forecast_forecast', ['public_id'], unique=True)
    op.create_index(op.f('ix_forecast_forecast_recipient_id'), 'forecast_forecast', ['recipient_id'], unique=False)
    op.create_index(op.f('ix_forecast_forecast_reference'), 'forecast_forecast', ['reference'], unique=False)
    op.create_index(op.f('ix_forecast_forecast_sector'), 'forecast_forecast', ['sector'], unique=False)
    op.create_index(op.f('ix_forecast_forecast_user_id'), 'forecast_forecast', ['user_id'], unique=False)
    # ### end Alembic commands ###

    op.execute("COMMIT")
    op.execute("ALTER TYPE event ADD VALUE 'ON_FORECAST_RECEIVED';")


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_forecast_forecast_user_id'), table_name='forecast_forecast')
    op.drop_index(op.f('ix_forecast_forecast_sector'), table_name='forecast_forecast')
    op.drop_index(op.f('ix_forecast_forecast_reference'), table_name='forecast_forecast')
    op.drop_index(op.f('ix_forecast_forecast_recipient_id'), table_name='forecast_forecast')
    op.drop_index(op.f('ix_forecast_forecast_public_id'), table_name='forecast_forecast')
    op.drop_index(op.f('ix_forecast_forecast_id'), table_name='forecast_forecast')
    op.drop_index(op.f('ix_forecast_forecast_end'), table_name='forecast_forecast')
    op.drop_index(op.f('ix_forecast_forecast_begin'), table_name='forecast_forecast')
    op.drop_table('forecast_forecast')
    # ### end Alembic commands ###

    op.execute("COMMIT")
    op.execute("ALTER TYPE event DROP VALUE 'ON_FORECAST_RECEIVED';")
