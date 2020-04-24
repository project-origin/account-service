import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy.exc import IntegrityError
from bip32utils import BIP32Key
from typing import List
from dataclasses import dataclass, field
from marshmallow import fields
from marshmallow_dataclass import NewType

from origin.db import ModelBase, atomic, inject_session
from origin.ledger import KeyGenerator


class User(ModelBase):
    """
    Represents one used in the system who is able to authenticate.
    """
    __tablename__ = 'auth_user'
    __table_args__ = (
        sa.UniqueConstraint('sub'),
    )

    id = sa.Column(sa.Integer, primary_key=True, index=True)
    created = sa.Column(sa.DateTime(timezone=True), server_default=sa.func.now())

    # Subject ID / Account number
    sub = sa.Column(sa.String(), index=True, unique=True, nullable=False)

    # Ledger master key
    master_extended_key = sa.Column(sa.String(), nullable=False)

    # Tokens
    access_token = sa.Column(sa.String(), nullable=False)
    refresh_token = sa.Column(sa.String(), nullable=False)
    token_expire = sa.Column(sa.DateTime(timezone=True), nullable=False)

    metering_points = relationship('MeteringPoint', uselist=True)

    def __str__(self):
        return 'User<%s>' % self.sub

    @property
    def key(self):
        """
        :rtype: BIP32Key
        """
        return KeyGenerator.get_key_for_user(self)

    @key.setter
    def key(self, value):
        """
        :param BIP32Key value:
        """
        KeyGenerator.set_key_for_user(self, value)

    def set_key_from_entropy(self, entropy):
        """
        :param str entropy:
        """
        KeyGenerator.set_key_for_user_from_entropy(self, entropy)


class MeteringPoint(ModelBase):
    """
    TODO
    """
    __tablename__ = 'accounts_meteringpoint'
    __table_args__ = (
        sa.UniqueConstraint('user_id', 'key_index'),
    )

    id: int = sa.Column(sa.Integer(), primary_key=True, index=True)
    user_id: int = sa.Column(sa.Integer(), sa.ForeignKey('auth_user.id'), index=True, nullable=False)
    user = relationship('User', foreign_keys=[user_id])
    gsrn = sa.Column(sa.String(), unique=True, index=True, nullable=False)
    sector = sa.Column(sa.String(), nullable=False)

    # Ledger key
    key_index = sa.Column(sa.Integer(), nullable=False)

    def __str__(self):
        return 'MeteringPoint<gsrn=%s>' % self.gsrn

    @staticmethod
    def create(user, **kwargs):
        """
        :param User user:
        :param kwargs:
        :rtype: MeteringPoint
        """
        return MeteringPoint(
            user=user,
            key_index=MeteringPointIndexSequence.get_next_position(user.id),
            **kwargs
        )

    @property
    def key(self):
        """
        :rtype: BIP32Key
        """
        return KeyGenerator.get_key_for_metering_point(self)

    @property
    def extended_key(self):
        """
        :rtype: str
        """
        return self.key.ExtendedKey()


class MeteringPointIndexSequence(ModelBase):
    """
    TODO
    """
    __tablename__ = 'accounts_meteringpoint_index_sequence'
    __table_args__ = (
        sa.UniqueConstraint('user_id', 'index'),
    )

    id = sa.Column(sa.Integer(), primary_key=True, index=True)
    user_id = sa.Column(sa.Integer(), sa.ForeignKey('auth_user.id'), index=True, nullable=False)
    index = sa.Column(sa.Integer(), nullable=False)

    @staticmethod
    @inject_session
    def get_next_position(user_id, session):
        """
        :param User user_id:
        :param Session session:
        :rtype: int
        """
        index = session \
            .query(sa.func.max(MeteringPointIndexSequence.index)) \
            .filter_by(user_id=user_id) \
            .scalar()

        @atomic
        def __insert(pos, session):
            session.add(MeteringPointIndexSequence(
                user_id=user_id,
                index=pos,
            ))

        while 1:
            if index is not None:
                index += 1
            else:
                index = 0

            try:
                __insert(index)
            except IntegrityError:
                # Unique constraint violated
                continue
            else:
                return index


# -- OnMeteringPointsAvailableWebhook request and response -------------------


@dataclass
class OnMeteringPointsAvailableWebhookRequest:
    sub: str


# -- Login request and response --------------------------------------------


@dataclass
class LoginRequest:
    return_url: str = field(metadata=dict(data_key='returnUrl'))


# -- VerifyLoginCallback request and response --------------------------------


Scope = NewType(
    name='Scope',
    typ=List[str],
    field=fields.Function,
    deserialize=lambda scope: scope.split(' '),
)


@dataclass
class VerifyLoginCallbackRequest:
    scope: Scope
    code: str
    state: str
