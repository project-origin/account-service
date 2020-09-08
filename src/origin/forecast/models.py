import isodate
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List

import sqlalchemy as sa
from marshmallow import fields, ValidationError, validate
from marshmallow_dataclass import NewType
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY

from origin.auth import sub_exists
from origin.db import ModelBase


# -- Database models ---------------------------------------------------------


class Forecast(ModelBase):
    """
    Implementation of a single GGO.
    """
    __tablename__ = 'forecast_forecast'

    id = sa.Column(sa.Integer(), primary_key=True, index=True)
    public_id = sa.Column(sa.String(), index=True, unique=True, nullable=False)
    created = sa.Column(sa.DateTime(timezone=True), server_default=sa.func.now())

    begin = sa.Column(sa.DateTime(timezone=True), nullable=False, index=True)
    end = sa.Column(sa.DateTime(timezone=True), nullable=False, index=True)
    sector = sa.Column(sa.String(), index=True, nullable=False)
    reference = sa.Column(sa.String(), index=True, nullable=False)
    forecast = sa.Column(ARRAY(sa.Integer()), nullable=False)

    # Data resolution (in seconds)
    resolution = sa.Column(sa.Integer(), nullable=False)

    # Sender
    user_id = sa.Column(sa.Integer(), sa.ForeignKey('auth_user.id'), index=True, nullable=False)
    user = relationship('User', foreign_keys=[user_id], lazy='joined')

    # Recipient
    recipient_id = sa.Column(sa.Integer(), sa.ForeignKey('auth_user.id'), index=True, nullable=False)
    recipient = relationship('User', foreign_keys=[recipient_id], lazy='joined')

    @property
    def resolution_timedelta(self):
        """
        :rtype: timedelta
        """
        return timedelta(seconds=self.resolution)


# -- Common ------------------------------------------------------------------


def validate_iso8601_duration(d):
    if d.total_seconds() <= 0:
        raise ValidationError('Duration too short')


def deserialize_iso8601_duration(s):
    try:
        return isodate.parse_duration(s)
    except isodate.isoerror.ISO8601Error:
        raise ValidationError('Invalid ISO8601 duration')


ForecastDuration = NewType(
    name='ForecastDuration',
    typ=int,
    field=fields.Function,
    deserialize=deserialize_iso8601_duration,
    serialize=lambda f: isodate.duration_isoformat(timedelta(seconds=f.resolution)),
    validate=validate_iso8601_duration,
)


ForecastSender = NewType(
    name='ForecastSender',
    typ=int,
    field=fields.Function,
    serialize=lambda f: f.user.sub,
)


ForecastRecipient = NewType(
    name='ForecastRecipient',
    typ=int,
    field=fields.Function,
    serialize=lambda f: f.recipient.sub,
)


@dataclass
class MappedForecast:
    """
    A reflection of the Forecast class above, but supports JSON schema
    serialization/deserialization using marshmallow/marshmallow-dataclass.
    """
    public_id: str = field(metadata=dict(data_key='id'))
    sender: ForecastSender
    recipient: ForecastRecipient
    created: datetime
    begin: datetime
    end: datetime
    sector: str
    reference: str
    forecast: List[int]
    resolution: ForecastDuration


# -- GetForecast request and response ----------------------------------------


@dataclass
class GetForecastRequest:
    public_id: str = field(default=None, metadata=dict(data_key='id'))
    reference: str = field(default=None)
    at_time: datetime = field(default=None, metadata=dict(data_key='atTime'))


@dataclass
class GetForecastResponse:
    success: bool
    forecast: MappedForecast


# -- GetForecastList request and response ------------------------------------


@dataclass
class GetForecastListRequest:
    offset: int = field(default=0)
    limit: int = field(default=None)
    reference: str = field(default=None)
    at_time: datetime = field(default=None, metadata=dict(data_key='atTime'))


@dataclass
class GetForecastListResponse:
    success: bool
    total: int
    forecasts: List[MappedForecast]


# -- GetForecastSeries request and response ----------------------------------


@dataclass
class GetForecastSeriesResponse:
    success: bool
    sent: List[str]
    received: List[str]


# -- SubmitForecast request and response -------------------------------------


@dataclass
class SubmitForecastRequest:
    account: str = field(metadata=dict(validate=sub_exists))
    reference: str
    sector: str
    begin: datetime
    resolution: ForecastDuration
    forecast: List[int] = field(metadata=dict(validate=validate.Length(min=1)))


@dataclass
class SubmitForecastResponse:
    success: bool
    id: str
