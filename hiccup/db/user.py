import hashlib
import os
from datetime import timedelta, datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, func, Sequence, LargeBinary, BigInteger

from hiccup.db.base import Base

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidKey


user_id_sequence = Sequence('user_id_seq', start=1)


class AnonymousIdentify(Base):
    __tablename__ = 'anonymous_identify'
    id = Column(BigInteger, user_id_sequence, server_default=user_id_sequence.next_value(), primary_key=True)
    public_key = Column(LargeBinary(length=32), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    @staticmethod
    def is_valid_ed25519_public_key(public_key: bytes) -> bool:
        if (len(public_key) % 32) != 0:
            return False

        try:
            ed25519.Ed25519PublicKey.from_public_bytes(public_key)
            return True
        except InvalidKey:
            return False


class ClassicIdentify(Base):
    __tablename__ = 'classic_identify'
    id = Column(BigInteger, user_id_sequence, server_default=user_id_sequence.next_value(), primary_key=True)
    user_name = Column(String(length=32), nullable=False, unique=True, index=True)
    password = Column(LargeBinary(length=64), nullable=False)
    salt = Column(LargeBinary(length=16), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    @staticmethod
    def encrypt_password(password: bytes, salt: Optional[bytes] = None) -> (bytes, bytes):
        if salt is None:
            salt = os.urandom(16)
        derived_key = hashlib.scrypt(password, salt=salt, n=2**14, r=8, p=1, dklen=64)
        return derived_key, salt

    def is_password_valid(self, password: bytes) -> bool:
        salt = self.salt
        derived_key, salt = self.encrypt_password(password, salt)
        return self.password == derived_key


class AuthToken(Base):
    __tablename__ = 'auth_token'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    token = Column(String(length=32), nullable=False, unique=True, index=True)
    issued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __init__(self, *, valid_duration: Optional[int] = None, **kwargs):
        super().__init__(**kwargs)
        if 'revoked_at' not in kwargs:
            if valid_duration is None:
                valid_duration = 86400
            self.revoked_at = datetime.now() + timedelta(seconds=valid_duration)
