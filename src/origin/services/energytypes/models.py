from typing import List, Dict
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class EmissionPart:
    technology: str
    share: float
    emissions: Dict[str, float]


@dataclass
class EmissionData:
    sector: str
    timestamp_utc: datetime
    emissions: Dict[str, float] = field(metadata=dict(data_key='mix_emissions'))
    parts: List[EmissionPart]
    amount: int


@dataclass
class GetMixEmissionsResponse:
    success: bool
    mix_emissions: List[EmissionData]
