import hashlib
import os
import string
from datetime import timedelta, datetime
import random
from typing import Optional

from cryptography.exceptions import InvalidKey, InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519
from sqlalchemy import Column, String, DateTime, func, Sequence, LargeBinary, BigInteger, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship, validates

from hiccup import SETTINGS
from hiccup.db.base import Base

user_id_sequence = Sequence('user_id_seq', start=1)


class AnonymousIdentify(Base):
    __tablename__ = 'anonymous_identify'
    id = Column(BigInteger, user_id_sequence, server_default=user_id_sequence.next_value(), primary_key=True)
    public_key = Column(LargeBinary(length=32), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    auth_tokens = relationship('AuthToken', back_populates='anonymous_identify')

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

    auth_tokens = relationship('AuthToken', back_populates='classic_identify')

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
    token = Column(String(length=64), nullable=False, unique=True, index=True)
    anonymous_user_id = Column(BigInteger, ForeignKey('anonymous_identify.id'), nullable=True)
    classic_user_id = Column(BigInteger, ForeignKey('classic_identify.id'), nullable=True)
    issued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    anonymous_identify = relationship('AnonymousIdentify', back_populates='auth_tokens')
    classic_identify = relationship('ClassicIdentify', back_populates='auth_tokens')

    __table_args__ = (
        CheckConstraint(
            '((anonymous_user_id IS NOT NULL AND classic_user_id IS NULL) OR '
            '(anonymous_user_id IS NULL AND classic_user_id IS NOT NULL))',
            name='check_anonymous_or_classic_user'
        ),
    )

    def __init__(self, *, valid_duration: Optional[int] = None, **kwargs):
        super().__init__(**kwargs)
        if 'revoked_at' not in kwargs:
            if valid_duration is None:
                valid_duration = SETTINGS.session_valid_duration
            self.revoked_at = datetime.now() + timedelta(seconds=valid_duration)

    @validates('anonymous_user_id', 'classic_user_id')
    def validate_user_ids(self, key, value):
        if key == 'anonymous_user_id':
            if value is not None and self.classic_user_id is not None:
                raise ValueError("Both anonymous_user_id and classic_user_id cannot have values at the same time.")
        elif key == 'classic_user_id':
            if value is not None and self.anonymous_user_id is not None:
                raise ValueError("Both anonymous_user_id and classic_user_id cannot have values at the same time.")

        if self.anonymous_user_id is None and self.classic_user_id is None and value is None:
            raise ValueError("Either anonymous_user_id or classic_user_id must have a value.")

        return value

    @staticmethod
    def new_classic_token(uid: int) -> 'AuthToken':
        token = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(64))
        return AuthToken(token=token, classic_user_id=uid)

    @staticmethod
    def new_anonymous_token(uid: int) -> 'AuthToken':
        token = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(64))
        return AuthToken(token=token, anonymous_user_id=uid)


def check_ed25519_signature(*, public_key: bytes, message: bytes, signature: bytes) -> bool:
    public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key)
    try:
        public_key.verify(signature, message)
        return True
    except InvalidSignature:
        pass

    return False
