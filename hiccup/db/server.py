from functools import cached_property
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Integer, String, JSON, func, ForeignKey, Boolean, DateTime, Table, BigInteger
from sqlalchemy.orm import relationship

from hiccup.db.base import Base


user_joined_server_table = Table(
    'user_joined_server', Base.metadata,
    Column('classic_user_id', Integer, ForeignKey('classic_identify.id'), primary_key=True),
    Column('virtual_server_id', Integer, ForeignKey('virtual_server.id'), primary_key=True),
)


class VirtualServer(Base):
    __tablename__ = 'virtual_server'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(length=64), nullable=False, default='Default Name')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    configuration = Column(JSON(), default=dict)

    channels = relationship('Channel', back_populates='virtual_server', cascade='all, delete, delete-orphan')
    virtual_server_aliases = relationship('VirtualServerAlias', back_populates='virtual_server')
    joined_users = relationship('ClassicIdentify', secondary=user_joined_server_table, back_populates='joined_servers')

    @cached_property
    def config(self) -> 'ServerConfiguration':
        return ServerConfiguration.model_validate(self.configuration)


class Channel(Base):
    __tablename__ = 'channel'
    id = Column(Integer, primary_key=True, autoincrement=True)
    server_id = Column(Integer, ForeignKey('virtual_server.id'), nullable=False)
    name = Column(String(length=64), nullable=False, default='Default Name')
    joinable = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    configuration = Column(JSON(), default=dict)

    virtual_server = relationship('VirtualServer', back_populates='channels')


class VirtualServerAlias(Base):
    __tablename__ = 'virtual_server_alias'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(length=64), nullable=False, unique=True, index=True)
    virtual_server_id = Column(Integer, ForeignKey('virtual_server.id'), nullable=False)
    valid = Column(Boolean, nullable=False, server_default='true', default=True)

    virtual_server = relationship('VirtualServer', back_populates='virtual_server_aliases')


class ServerConfiguration(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    allow_join_by_alias: Optional[bool] = Field(True)
