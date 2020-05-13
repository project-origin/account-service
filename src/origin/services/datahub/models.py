from enum import Enum
from typing import List
from datetime import datetime
from itertools import zip_longest
from dataclasses import dataclass, field
from marshmallow_dataclass import NewType

from origin.common import DateTimeRange


# -- Common ------------------------------------------------------------------


class MeasurementType(Enum):
    PRODUCTION = 'production'
    CONSUMPTION = 'consumption'


class SummaryResolution(Enum):
    """
    TODO
    """
    ALL = 'all'
    YEAR = 'year'
    MONTH = 'month'
    DAY = 'day'
    HOUR = 'hour'


SummaryGroupValue = NewType('SummaryGroupValue', int, allow_none=True)


@dataclass
class SummaryGroup:
    """
    TODO
    """
    group: List[str] = field(default_factory=list)
    values: List[SummaryGroupValue] = field(default_factory=list)

    def __add__(self, other):
        """
        :param SummaryGroup other:
        :rtype: SummaryGroup
        """
        if not isinstance(other, SummaryGroup):
            return NotImplemented

        values = []

        for v1, v2 in zip_longest(self.values, other.values, fillvalue=None):
            if v1 is not None and v2 is not None:
                values.append(v1 + v2)
            elif v1 is not None:
                values.append(v1)
            elif v2 is not None:
                values.append(v2)
            else:
                values.append(None)

        return SummaryGroup(self.group, values)

    def __radd__(self, other):
        """
        :param SummaryGroup other:
        :rtype: SummaryGroup
        """
        return self + other


class MeteringPointType(Enum):
    PRODUCTION = 'production'
    CONSUMPTION = 'consumption'


@dataclass
class MeteringPoint:
    gsrn: str
    type: MeteringPointType = field(metadata=dict(by_value=True))
    sector: str
    technology_code: str = field(default=None, metadata=dict(data_key='technologyCode'))
    fuel_code: str = field(default=None, metadata=dict(data_key='fuelCode'))
    street_code: str = field(default=None, metadata=dict(data_key='streetCode'))
    street_name: str = field(default=None, metadata=dict(data_key='streetName'))
    building_number: str = field(default=None, metadata=dict(data_key='buildingNumber'))
    city_name: str = field(default=None, metadata=dict(data_key='cityName'))
    postcode: str = field(default=None, metadata=dict(data_key='postCode'))
    municipality_code: str = field(default=None, metadata=dict(data_key='municipalityCode'))


@dataclass
class Measurement:
    address: str
    gsrn: str
    begin: datetime
    end: datetime
    type: MeasurementType = field(metadata=dict(by_value=True))
    sector: str
    amount: int


@dataclass
class MeasurementFilters:
    """
    TODO
    """
    begin: datetime = field(default=None)
    begin_range: DateTimeRange = field(default=None, metadata=dict(data_key='beginRange'))
    sector: List[str] = field(default_factory=list)
    gsrn: List[str] = field(default_factory=list)
    type: MeasurementType = field(default=None, metadata=dict(by_value=True))


@dataclass
class Ggo:
    address: str
    gsrn: str
    begin: datetime
    end: datetime
    sector: str
    amount: int
    issue_time: str = field(metadata=dict(data_key='issueTime'))
    expire_time: str = field(metadata=dict(data_key='expireTime'))
    technology_code: str = field(default=None, metadata=dict(data_key='technologyCode'))
    fuel_code: str = field(default=None, metadata=dict(data_key='fuelCode'))


# -- GetMeasurement request and response -------------------------------------


@dataclass
class SetKeyRequest:
    gsrn: str
    key: str


@dataclass
class SetKeyResponse:
    success: bool


# -- GetGgoList request and response -----------------------------------------


@dataclass
class GetGgoListRequest:
    gsrn: str
    begin_range: DateTimeRange = field(metadata=dict(data_key='beginRange'))


@dataclass
class GetGgoListResponse:
    success: bool
    ggos: List[Ggo] = field(default_factory=list)


# -- GetMeasurement request and response -------------------------------------


@dataclass
class GetMeasurementRequest:
    gsrn: str
    begin: datetime


@dataclass
class GetMeasurementResponse:
    success: bool
    measurement: Measurement


# -- GetMeasurementList request and response ---------------------------------


@dataclass
class GetMeasurementListRequest:
    filters: MeasurementFilters
    offset: int
    limit: int


@dataclass
class GetMeasurementListResponse:
    success: bool
    total: int
    measurements: List[Measurement] = field(default_factory=list)


# -- GetGgoSummary request and response --------------------------------------


@dataclass
class GetMeasurementSummaryRequest:
    resolution: SummaryResolution = field(metadata=dict(by_value=True))
    filters: MeasurementFilters
    fill: bool
    grouping: List[str] = field(default_factory=list)


@dataclass
class GetMeasurementSummaryResponse:
    success: bool
    labels: List[str] = field(default_factory=list)
    groups: List[SummaryGroup] = field(default_factory=list)


# -- GetMeteringPoints request and response ----------------------------------


@dataclass
class GetMeteringPointsResponse:
    success: bool
    meteringpoints: List[MeteringPoint] = field(default_factory=list)


# -- Webhooks request and response -------------------------------------------


@dataclass
class WebhookSubscribeRequest:
    url: str


@dataclass
class WebhookSubscribeResponse:
    success: bool
