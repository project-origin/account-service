import sqlalchemy as sa
from enum import Enum
from dataclasses import dataclass

from origin.db import ModelBase
from origin.ggo import MappedGgo
from origin.forecast import MappedForecast


@dataclass
class OnGgoReceivedRequest:
    sub: str
    ggo: MappedGgo


@dataclass
class OnForecastReceivedRequest:
    sub: str
    forecast: MappedForecast


class WebhookEvent(Enum):
    ON_GGO_RECEIVED = 'ON_GGO_RECEIVED'
    ON_FORECAST_RECEIVED = 'ON_FORECAST_RECEIVED'


class WebhookSubscription(ModelBase):
    """
    Represents one used in the system who is able to authenticate.
    """
    __tablename__ = 'webhook_subscription'
    __table_args__ = (
        sa.UniqueConstraint('subject', 'event', 'url'),
    )

    id = sa.Column(sa.Integer(), primary_key=True, index=True)
    event = sa.Column(sa.Enum(WebhookEvent), index=True, nullable=False)
    subject = sa.Column(sa.String(), index=True, nullable=False)
    url = sa.Column(sa.String(), nullable=False)
    secret = sa.Column(sa.String(), nullable=True)


# -- Subscribe request and response ------------------------------------------


@dataclass
class SubscribeRequest:
    url: str
    secret: str
