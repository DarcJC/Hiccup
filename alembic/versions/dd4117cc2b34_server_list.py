"""server_list

Revision ID: dd4117cc2b34
Revises: 24216e69f8a4
Create Date: 2024-08-31 18:31:56.881067

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dd4117cc2b34'
down_revision: Union[str, None] = '24216e69f8a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user_joined_server',
    sa.Column('classic_user_id', sa.Integer(), nullable=False),
    sa.Column('virtual_server_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['classic_user_id'], ['classic_identify.id'], ),
    sa.ForeignKeyConstraint(['virtual_server_id'], ['virtual_server.id'], ),
    sa.PrimaryKeyConstraint('classic_user_id', 'virtual_server_id')
    )
    op.create_table('virtual_server_alias',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('virtual_server_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['virtual_server_id'], ['virtual_server.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_virtual_server_alias_name'), 'virtual_server_alias', ['name'], unique=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_virtual_server_alias_name'), table_name='virtual_server_alias')
    op.drop_table('virtual_server_alias')
    op.drop_table('user_joined_server')
    # ### end Alembic commands ###
