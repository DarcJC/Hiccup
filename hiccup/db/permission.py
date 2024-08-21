from sqlalchemy import Column, BigInteger, ARRAY, String, Table, ForeignKey
from sqlalchemy.orm import relationship

from hiccup.db.base import Base


user_permission_group = Table(
    'user_permission_group', Base.metadata,
    Column('classic_user_id', BigInteger, ForeignKey('classic_identify.id'), primary_key=True),
    Column('permission_group_id', BigInteger, ForeignKey('permission_group.id'), primary_key=True),
)


class PermissionGroup(Base):
    __tablename__ = 'permission_group'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(length=255), nullable=False)
    permissions = Column(ARRAY(String(length=255)), nullable=False)

    classic_identifies = relationship(
        'ClassicIdentify',
        secondary=user_permission_group,
        back_populates='permission_groups',
    )

