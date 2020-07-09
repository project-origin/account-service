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
    mix_emissions: Dict[str, float]
    parts: List[EmissionPart]
    amount: int = field(default=1, metadata=dict(required=False, missing=1))


@dataclass
class GetMixEmissionsResponse:
    success: bool
    mix_emissions: List[EmissionData]
