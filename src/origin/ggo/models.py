import sqlalchemy as sa
import origin_ledger_sdk as ols
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship
from bip32utils import BIP32Key
from enum import Enum
from datetime import datetime, timezone
from typing import List
from dataclasses import dataclass, field
from marshmallow import validate

from origin.db import ModelBase, atomic, Session
from origin.auth import User, sub_exists, MeteringPoint
from origin.common import DateTimeRange
from origin.ledger import KeyGenerator
from origin.services.datahub import Measurement


# -- Database models ---------------------------------------------------------


class Ggo(ModelBase):
    """
    technology_type: solar, wind, oil, etc.
    technology_code: T010000, T030100, etc.
    source_code: F01010300, F01010500, etc.

    TODO issue date?
    TODO expire date?
    """
    __tablename__ = 'ggo_ggo'
    __table_args__ = (
        sa.UniqueConstraint('address'),
        sa.UniqueConstraint('user_id', 'key_index'),
    )

    id = sa.Column(sa.Integer(), primary_key=True, index=True)
    user_id = sa.Column(sa.Integer(), sa.ForeignKey('auth_user.id'), index=True, nullable=False)
    user = relationship('User', foreign_keys=[user_id], lazy='joined')

    # If this is a child of another GGO (in case a split/transfer happened)
    parent_id = sa.Column(sa.Integer(), sa.ForeignKey('ggo_ggo.id'), index=True)
    parent = relationship('Ggo', foreign_keys=[parent_id], uselist=False)
    children = relationship('Ggo', remote_side=[id], back_populates='parent', uselist=True)

    # Ledger data
    address = sa.Column(sa.String(), index=True, nullable=False)
    key_index = sa.Column(sa.Integer())

    # Dates
    issue_time = sa.Column(sa.DateTime(timezone=True), nullable=False, index=True)
    expire_time = sa.Column(sa.DateTime(timezone=True), nullable=False, index=True)
    begin = sa.Column(sa.DateTime(timezone=True), nullable=False, index=True)
    end = sa.Column(sa.DateTime(timezone=True), nullable=False)

    # GGO data
    amount = sa.Column(sa.Integer(), nullable=False)
    sector = sa.Column(sa.String(), nullable=False, index=True)
    technology_code = sa.Column(sa.String(), nullable=False, index=True)
    fuel_code = sa.Column(sa.String(), nullable=False, index=True)

    # Whether or not this GGO was originally issued (False means its
    # product of a trade/split)
    issued = sa.Column(sa.Boolean(), nullable=False, index=True, default=False)

    # Whether or not this GGO is currently stored (False means its
    # been transferred, split or retired)
    stored = sa.Column(sa.Boolean(), nullable=False, index=True, default=False)

    # Whether or not this GGO has been retired to a measurement
    retired = sa.Column(sa.Boolean(), nullable=False, index=True, default=False)

    # Whether or not this GGO has been synchronized onto the ledger
    synchronized = sa.Column(sa.Boolean(), nullable=False, index=True, default=False)

    # Whether or not this GGO is currently locked (True means that
    # a ledger operation is being executed with this GGO involved)
    locked = sa.Column(sa.Boolean(), nullable=False, index=True, default=False)

    # The GSRN number this GGO was issued at (if issued=True)
    issue_gsrn = sa.Column(sa.String(), sa.ForeignKey('accounts_meteringpoint.gsrn'), index=True)
    issue_meteringpoint = relationship('MeteringPoint', foreign_keys=[issue_gsrn], lazy='joined', uselist=False)

    # The GSRN and Measurement address this GGO is retired to (if retired=True)
    retire_gsrn = sa.Column(sa.String(), sa.ForeignKey('accounts_meteringpoint.gsrn'), index=True)
    retire_meteringpoint = relationship('MeteringPoint', foreign_keys=[retire_gsrn], lazy='joined', uselist=False)
    retire_address = sa.Column(sa.String(), index=True)

    def create_child(self, amount, user):
        """
        :param int amount:
        :param User user:
        :rtype: Ggo
        """
        assert 0 < amount <= self.amount

        key_index = GgoIndexSequence.get_next(user.id, Session.object_session(self))
        key = KeyGenerator.get_key_for_traded_ggo_at_index(user, key_index)
        address = ols.generate_address(ols.AddressPrefix.GGO, key.PublicKey())

        return Ggo(
            user_id=user.id,
            parent_id=self.id,
            address=address,
            key_index=key_index,
            issue_time=self.issue_time,
            expire_time=self.expire_time,
            begin=self.begin,
            sector=self.sector,
            end=self.end,
            technology_code=self.technology_code,
            fuel_code=self.fuel_code,
            amount=amount,
            issued=False,
            stored=False,
            retired=False,
            synchronized=False,
            locked=False,
        )

    @property
    def key(self):
        """
        :rtype: BIP32Key
        """
        if self.issued:
            return KeyGenerator.get_key_for_issued_ggo(self)
        else:
            return KeyGenerator.get_key_for_traded_ggo(self)

    @property
    def extended_key(self):
        """
        :rtype: str
        """
        return self.key.ExtendedKey()

    def is_tradable(self):
        """
        :rtype: bool
        """
        return not self.is_expired()

    def is_expired(self):
        """
        :rtype: bool
        """
        return datetime.now(tz=timezone.utc) >= self.expire_time


class GgoIndexSequence(ModelBase):
    """
    TODO
    """
    __tablename__ = 'ggo_ggo_index_sequence'
    __table_args__ = (
        sa.UniqueConstraint('user_id'),
    )

    id = sa.Column(sa.Integer(), primary_key=True, index=True)
    user_id = sa.Column(sa.Integer(), sa.ForeignKey('auth_user.id'), index=True, nullable=False)
    index = sa.Column(sa.Integer(), nullable=False)

    @staticmethod
    def get_next(user_id, session):
        """
        :param int user_id:
        :param Session session:
        :rtype: int
        """
        query = """
            WITH updated AS (
              INSERT INTO ggo_ggo_index_sequence (user_id, index)
              VALUES (:user_id, 0)
              ON CONFLICT (user_id)
              DO UPDATE
                SET index = ggo_ggo_index_sequence.index + 1
              RETURNING ggo_ggo_index_sequence.index
            )
            SELECT index FROM updated;
            """

        res = session.execute(query, {'user_id': user_id})
        key_index = list(res)[0][0]

        return key_index


class Technology(ModelBase):
    """
    A technology (by label) consists of a combination
    of technology_code and fuel_code.
    """
    __tablename__ = 'ggo_technology'
    __table_args__ = (
        sa.UniqueConstraint('technology_code', 'fuel_code'),
    )

    id = sa.Column(sa.Integer(), primary_key=True, index=True)
    technology = sa.Column(sa.String(), nullable=False)
    technology_code = sa.Column(sa.String(), index=True, nullable=False)
    fuel_code = sa.Column(sa.String(), index=True, nullable=False)


# -- Common ------------------------------------------------------------------


@dataclass
class MappedGgo:
    address: str
    sector: str
    begin: datetime
    end: datetime
    amount: int
    technology_code: str = field(default=None, metadata=dict(data_key='technologyCode'))
    fuel_code: str = field(default=None, metadata=dict(data_key='fuelCode'))


class GgoCategory(Enum):
    """
    TODO
    """
    ISSUED = 'issued'
    STORED = 'stored'
    RETIRED = 'retired'
    EXPIRED = 'expired'


@dataclass
class GgoFilters:
    """
    TODO
    """
    begin: datetime = field(default=None)
    begin_range: DateTimeRange = field(default=None, metadata=dict(data_key='beginRange'))

    sector: List[str] = field(default_factory=list)
    technology_code: List[str] = field(default_factory=list, metadata=dict(data_key='technologyCode'))
    fuel_code: List[str] = field(default_factory=list, metadata=dict(data_key='fuelCode'))

    category: GgoCategory = field(default=None, metadata=dict(by_value=True))
    issue_gsrn: List[str] = field(default_factory=list, metadata=dict(data_key='issueGsrn'))
    retire_gsrn: List[str] = field(default_factory=list, metadata=dict(data_key='retireGsrn'))

    # TODO begin and begin_range mutually exclusive


@dataclass
class TransferFilters(GgoFilters):
    """
    TODO
    """
    reference: List[str] = field(default_factory=list, metadata=dict(allow_none=True))

    # TODO add recipient user account?


@dataclass
class RetireFilters(GgoFilters):
    """
    TODO
    """
    gsrn: List[str] = field(default_factory=list)
    address: List[str] = field(default_factory=list)


class TransferDirection(Enum):
    """
    TODO
    """
    INBOUND = 'inbound'
    OUTBOUND = 'outbound'


@dataclass
class TransferRequest:
    """
    TODO
    """
    amount: int = field(metadata=dict(validate=validate.Range(min=1)))
    reference: str
    sub: str = field(metadata=dict(required=True, validate=sub_exists))


@dataclass
class RetireRequest:
    """
    TODO
    """
    amount: int = field(metadata=dict(validate=validate.Range(min=1)))
    gsrn: str


class SummaryResolution(Enum):
    """
    TODO
    """
    ALL = 'all'
    YEAR = 'year'
    MONTH = 'month'
    DAY = 'day'
    HOUR = 'hour'


@dataclass
class SummaryGroup:
    """
    TODO
    """
    group: List[str] = field(default_factory=list)
    values: List[int] = field(default_factory=list)


# -- GetGgoList request and response -----------------------------------------


@dataclass
class GetGgoListRequest:
    filters: GgoFilters
    offset: int
    limit: int
    order: List[str] = field(default_factory=list)


@dataclass
class GetGgoListResponse:
    success: bool
    total: int
    results: List[MappedGgo] = field(default_factory=list)


# -- GetGgoSummary request and response --------------------------------------


@dataclass
class GetGgoSummaryRequest:
    resolution: SummaryResolution = field(metadata=dict(by_value=True))
    filters: GgoFilters
    fill: bool

    grouping: List[str] = field(metadata=dict(validate=(
        validate.ContainsOnly(('begin', 'sector', 'technology', 'technologyCode', 'fuelCode')),
    )))


@dataclass
class GetGgoSummaryResponse:
    success: bool
    labels: List[str] = field(default_factory=list)
    groups: List[SummaryGroup] = field(default_factory=list)


# -- GetTransferSummary request and response ---------------------------------


@dataclass
class GetTransferSummaryRequest:
    resolution: SummaryResolution = field(metadata=dict(by_value=True))
    filters: TransferFilters
    fill: bool

    grouping: List[str] = field(metadata=dict(validate=(
        validate.ContainsOnly(('begin', 'sector', 'technology', 'technologyCode', 'fuelCode')),
    )))

    direction: TransferDirection = field(default=None, metadata=dict(by_value=True))


@dataclass
class GetTransferSummaryResponse(GetGgoSummaryResponse):
    pass


# -- ComposeGgo request and response -----------------------------------------


@dataclass
class ComposeGgoRequest:
    address: str
    transfers: List[TransferRequest]
    retires: List[RetireRequest]


@dataclass
class ComposeGgoResponse:
    success: bool
    message: str = field(default=None)


# -- GetTransferredAmount request and response -------------------------------


@dataclass
class GetTransferredAmountRequest:
    filters: TransferFilters
    direction: TransferDirection = field(default=None, metadata=dict(by_value=True))


@dataclass
class GetTransferredAmountResponse:
    success: bool
    amount: int


# -- GetRetiredAmount request and response -----------------------------------


@dataclass
class GetRetiredAmountRequest:
    filters: RetireFilters


@dataclass
class GetRetiredAmountResponse:
    success: bool
    amount: int


# -- OnGgosIssuedWebhook request and response --------------------------------


@dataclass
class OnGgosIssuedWebhookRequest:
    sub: str
    gsrn: str
    begin: datetime
