import marshmallow
from typing import List
from datetime import datetime
from dataclasses import dataclass
from marshmallow_dataclass import NewType

from origin.common import EmissionValues


EmissionValuesType = NewType(
    name='EmissionValuesType',
    typ=dict,
    field=marshmallow.fields.Function,
    deserialize=lambda emissions: EmissionValues(**emissions),
)


@dataclass
class EmissionPart:
    technology: str

    # Consumed amount in Wh
    amount: int

    # Emissions in gram
    emissions: EmissionValuesType


@dataclass
class EmissionData:
    sector: str
    timestamp_utc: datetime
    parts: List[EmissionPart]

    class Meta:
        unknown = marshmallow.EXCLUDE

    @property
    def amount(self):
        """
        Returns Emissions in gram

        :rtype: int
        """
        return sum(part.amount for part in self.parts)

    @property
    def emissions(self):
        """
        Returns Emissions in gram

        :rtype: EmissionValues[str, float]
        """
        return sum((part.emissions for part in self.parts), EmissionValues())

    @property
    def emissions_per_wh(self):
        """
        Returns Emissions per Wh (gram/Wh)

        :rtype: EmissionValues[str, float]
        """
        amount = self.amount

        if amount > 0:
            return self.emissions / amount
        else:
            return EmissionValues()

    @property
    def emissions_per_wh_per_technology(self):
        """
        Returns Emissions per Wh per technology (gram/Wh)

        :rtype: EmissionValues[str, float]
        """
        amount = self.amount

        if amount > 0:
            return self.technologies / amount
        else:
            return EmissionValues()

    @property
    def technologies(self):
        """
        Returns consumed amount per technology

        :rtype: EmissionValues[str, int]
        """
        return EmissionValues(**{
            part.technology: part.amount for part in self.parts
        })


@dataclass
class GetMixEmissionsResponse:
    success: bool
    mix_emissions: List[EmissionData]
