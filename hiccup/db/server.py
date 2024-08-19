from sqlalchemy import Column, Integer, String, JSON, func, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship

from hiccup.db.base import Base


class VirtualServer(Base):
    __tablename__ = 'virtual_server'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(length=64), nullable=False, default='Default Name')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    configuration = Column(JSON(), default=dict)

    channels = relationship('Channel', back_populates='virtual_server', cascade='all, delete, delete-orphan')


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
