"""Init

Revision ID: 901e3bb6cecc
Revises: 
Create Date: 2024-08-19 18:52:25.704033

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from hiccup.db.user import user_id_sequence

# revision identifiers, used by Alembic.
revision: str = '901e3bb6cecc'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.schema.CreateSequence(user_id_sequence))
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('anonymous_identify',
    sa.Column('id', sa.Integer(), server_default=sa.text("nextval('user_id_seq')"), nullable=False),
    sa.Column('public_key', sa.LargeBinary(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_anonymous_identify_public_key'), 'anonymous_identify', ['public_key'], unique=True)
    op.create_table('auth_token',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('token', sa.String(length=32), nullable=False),
    sa.Column('issued_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_auth_token_token'), 'auth_token', ['token'], unique=True)
    op.create_table('classic_identify',
    sa.Column('id', sa.Integer(), server_default=sa.text("nextval('user_id_seq')"), nullable=False),
    sa.Column('user_name', sa.String(length=32), nullable=False),
    sa.Column('password', sa.LargeBinary(length=64), nullable=False),
    sa.Column('salt', sa.LargeBinary(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_classic_identify_password'), 'classic_identify', ['password'], unique=True)
    op.create_index(op.f('ix_classic_identify_salt'), 'classic_identify', ['salt'], unique=True)
    op.create_index(op.f('ix_classic_identify_user_name'), 'classic_identify', ['user_name'], unique=True)
    op.create_table('virtual_server',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('configuration', sa.JSON(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('channel',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('server_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('joinable', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('configuration', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['server_id'], ['virtual_server.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('channel')
    op.drop_table('virtual_server')
    op.drop_index(op.f('ix_classic_identify_user_name'), table_name='classic_identify')
    op.drop_index(op.f('ix_classic_identify_salt'), table_name='classic_identify')
    op.drop_index(op.f('ix_classic_identify_password'), table_name='classic_identify')
    op.drop_table('classic_identify')
    op.drop_index(op.f('ix_auth_token_token'), table_name='auth_token')
    op.drop_table('auth_token')
    op.drop_index(op.f('ix_anonymous_identify_public_key'), table_name='anonymous_identify')
    op.drop_table('anonymous_identify')
    # ### end Alembic commands ###
    op.execute(sa.schema.DropSequence(user_id_sequence))
