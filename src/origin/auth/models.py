import sqlalchemy as sa
from sqlalchemy.orm import relationship
from enum import Enum
from bip32utils import BIP32Key
from typing import List
from dataclasses import dataclass, field
from marshmallow import fields
from marshmallow_dataclass import NewType

from origin.common import DateTimeRange, DateRange
from origin.db import ModelBase
from origin.ledger import KeyGenerator
from origin.services.datahub import MeteringPoint as DataHubMeteringPoint


class User(ModelBase):
    """
    Implementation of a single user in the system who is able to authenticate.
    """
    __tablename__ = 'auth_user'
    __table_args__ = (
        sa.UniqueConstraint('sub'),
    )

    id = sa.Column(sa.Integer, primary_key=True, index=True)
    created = sa.Column(sa.DateTime(timezone=True), server_default=sa.func.now())
    last_login = sa.Column(sa.DateTime(timezone=True))
    active = sa.Column(sa.Boolean(), nullable=False, default=True)

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
        :param bytes entropy:
        """
        KeyGenerator.set_key_for_user_from_entropy(self, entropy)

    def update_last_login(self):
        self.last_login = sa.func.now()


class MeteringPointType(Enum):
    PRODUCTION = 'production'
    CONSUMPTION = 'consumption'


class MeteringPoint(ModelBase):
    """
    Implementation of a single MeteringPoint, which belongs to a user.

    MeteringPoints are imported from DataHubService, and should always be
    a 1-to-1 reflection of the MeteringPoints available in DataHub.

    Each MeteringPoint has a key_index, which is unique per user.
    The table MeteringPointIndexSequence (below) is used to increment the
    key_index every time a new MeteringPoint i created using the
    MeteringPoint.create() method. The key_index is used when calculating/
    generating a key for the specific MeteringPoint.
    """
    __tablename__ = 'accounts_meteringpoint'
    __table_args__ = (
        sa.UniqueConstraint('gsrn'),
        sa.UniqueConstraint('user_id', 'key_index'),
    )

    id: int = sa.Column(sa.Integer(), primary_key=True, index=True)
    user_id: int = sa.Column(sa.Integer(), sa.ForeignKey('auth_user.id'), index=True, nullable=False)
    user = relationship('User', foreign_keys=[user_id])
    gsrn = sa.Column(sa.String(), unique=True, index=True, nullable=False)
    sector = sa.Column(sa.String(), nullable=False)
    type: MeteringPointType = sa.Column(sa.Enum(MeteringPointType), nullable=True)

    # Ledger key
    key_index = sa.Column(sa.Integer(), nullable=False)

    def __str__(self):
        return 'MeteringPoint<gsrn=%s>' % self.gsrn

    @staticmethod
    def create(user, session, **kwargs):
        """
        :param User user:
        :param kwargs:
        :rtype: MeteringPoint
        """
        return MeteringPoint(
            user_id=user.id,
            key_index=MeteringPointIndexSequence.get_next_position(user.id, session),
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
    Keeps track of indexes for MeteringPoints, which are unique per user.
    Call get_next_position() to increment the index while simultaneously
    returning the new index.

    Be aware that this operation locks the table row, possible the entire
    table, so its important to commit/rollback the transaction as soon as
    possible.
    """
    __tablename__ = 'accounts_meteringpoint_index_sequence'
    __table_args__ = (
        sa.UniqueConstraint('user_id'),
    )

    id = sa.Column(sa.Integer(), primary_key=True, index=True)
    user_id = sa.Column(sa.Integer(), sa.ForeignKey('auth_user.id'), index=True, nullable=False)
    index = sa.Column(sa.Integer(), nullable=False)

    @staticmethod
    def get_next_position(user_id, session):
        """
        :param User user_id:
        :param Session session:
        :rtype: int
        """
        query = """
            WITH updated AS (
              INSERT INTO accounts_meteringpoint_index_sequence (user_id, index)
              VALUES (:user_id, 0)
              ON CONFLICT (user_id)
              DO UPDATE
                SET index = accounts_meteringpoint_index_sequence.index + 1
              RETURNING accounts_meteringpoint_index_sequence.index
            )
            SELECT index FROM updated;
            """

        res = session.execute(query, {'user_id': user_id})
        key_index = list(res)[0][0]

        return key_index


# -- OnMeteringPointsAvailableWebhook request and response -------------------


@dataclass
class OnMeteringPointAvailableWebhookRequest:
    sub: str
    meteringpoint: DataHubMeteringPoint


@dataclass
class OnMeteringPointsAvailableWebhookRequest:
    # TODO remove
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


# -- GetAccounts request and response ----------------------------------------


@dataclass
class Account:
    id: str


@dataclass
class GetAccountsResponse:
    success: bool
    accounts: List[Account]


# -- SearchSuppliers request and response ------------------------------------


@dataclass
class FindSuppliersRequest:
    date_range: DateRange = field(metadata=dict(data_key='dateRange'))
    min_amount: int = field(metadata=dict(data_key='minAmount'))
    min_coverage: float = field(metadata=dict(data_key='minCoverage'))


@dataclass
class FindSuppliersResponse:
    success: bool
    suppliers: List[str]
