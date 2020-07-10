from enum import IntEnum
from typing import List, Dict
from datetime import datetime
from dataclasses import dataclass, field

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
    total_emissions: Dict[str, float] = field(metadata=dict(data_key='totalEmissions'))
    total_emissions_per_wh: Dict[str, float] = field(metadata=dict(data_key='totalEmissionsPerWh'))


# -- GetEcoDeclaration request and response ----------------------------------


@dataclass
class GetEcoDeclarationRequest:
    gsrn: List[str]
    resolution: EcoDeclarationResolution
    begin_range: DateTimeRange = field(metadata=dict(data_key='beginRange'))


@dataclass
class GetEcoDeclarationResponse:
    success: bool
    general: MappedEcoDeclaration
    individual: MappedEcoDeclaration