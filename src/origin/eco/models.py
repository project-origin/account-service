from enum import IntEnum
from typing import List, Dict
from marshmallow import post_load
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta

from origin.common import DateTimeRange


class EcoDeclarationResolution(IntEnum):
    all = 0
    year = 1
    month = 2
    day = 3
    hour = 4


@dataclass
class MappedEcoDeclaration:
    emissions: Dict[datetime, Dict[str, float]] = field(metadata=dict(data_key='emissions'))
    emissions_per_wh: Dict[datetime, Dict[str, float]] = field(metadata=dict(data_key='emissionsPerWh'))
    consumed_amount: Dict[datetime, float] = field(metadata=dict(data_key='consumedAmount'))
    technologies: Dict[datetime, Dict[str, float]]
    total_emissions: Dict[str, float] = field(metadata=dict(data_key='totalEmissions'))
    total_emissions_per_wh: Dict[str, float] = field(metadata=dict(data_key='totalEmissionsPerWh'))
    total_consumed_amount: int = field(metadata=dict(data_key='totalConsumedAmount'))
    total_technologies: Dict[str, int] = field(metadata=dict(data_key='totalTechnologies'))


# -- GetEcoDeclaration request and response ----------------------------------


@dataclass
class GetEcoDeclarationRequest:
    gsrn: List[str]
    resolution: EcoDeclarationResolution
    begin_range: DateTimeRange = field(metadata=dict(data_key='beginRange'))

    # Offset from UTC in hours
    utc_offset: int = field(metadata=dict(data_key='utcOffset'))

    @post_load
    def apply_time_offset(self, data, **kwargs):
        tzinfo = timezone(timedelta(hours=data['utc_offset']))

        if data['begin_range'].begin.utcoffset() is None:
            data['begin_range'].begin = \
                data['begin_range'].begin.replace(tzinfo=tzinfo)

        if data['begin_range'].end.utcoffset() is None:
            data['begin_range'].end = \
                data['begin_range'].end.replace(tzinfo=tzinfo)

        return data


@dataclass
class GetEcoDeclarationResponse:
    success: bool
    general: MappedEcoDeclaration
    individual: MappedEcoDeclaration
