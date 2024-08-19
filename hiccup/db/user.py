from datetime import timedelta, datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, func, Sequence, LargeBinary

from hiccup.db.base import Base


user_id_sequence = Sequence('user_id_seq', start=1)


class AnonymousIdentify(Base):
    __tablename__ = 'anonymous_identify'
    id = Column(Integer, user_id_sequence, server_default=user_id_sequence.next_value(), primary_key=True)
    public_key = Column(LargeBinary(length=32), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class ClassicIdentify(Base):
    __tablename__ = 'classic_identify'
    id = Column(Integer, user_id_sequence, server_default=user_id_sequence.next_value(), primary_key=True)
    user_name = Column(String(length=32), nullable=False, unique=True, index=True)
    password = Column(LargeBinary(length=64), nullable=False, unique=True, index=True)
    salt = Column(LargeBinary(length=16), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class AuthToken(Base):
    __tablename__ = 'auth_token'
    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(length=32), nullable=False, unique=True, index=True)
    issued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __init__(self, *, valid_duration: Optional[int] = None, **kwargs):
        super().__init__(**kwargs)
        if 'revoked_at' not in kwargs:
            if valid_duration is None:
                valid_duration = 86400
            self.revoked_at = datetime.now() + timedelta(seconds=valid_duration)
