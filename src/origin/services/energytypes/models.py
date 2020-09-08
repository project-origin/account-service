import marshmallow
from typing import List
from itertools import groupby
from datetime import datetime, timezone
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
    def technologies(self):
        """
        Returns consumed amount per technology

        :rtype: EmissionValues[str, int]
        """
        return EmissionValues(**{
            part.technology: part.amount for part in self.parts
        })

    @property
    def technologies_share(self):
        """
        Returns consumed amount per technology

        :rtype: EmissionValues[str, int]
        """
        amount = self.amount

        if amount > 0:
            return self.technologies / amount
        else:
            return EmissionValues()


def parse_mix_emissions_timestamp(s):
    return datetime \
        .fromisoformat(s.replace('Z', '')) \
        .replace(tzinfo=timezone.utc)


def mix_emissions_to_emission_data(mix_emissions):
    mix_emissions_grouped = groupby(
        iterable=mix_emissions,
        key=lambda row: (parse_mix_emissions_timestamp(row['timestamp_utc']), row['sector']),
    )

    for (timestamp_utc, sector), rows in mix_emissions_grouped:
        parts = []

        for row in rows:
            emissions = EmissionValues(**{
                k: v for k, v in row.items()
                if k not in ('timestamp_utc', 'sector', 'technology', 'amount')
            })

            parts.append(EmissionPart(
                technology=row['technology'],
                amount=row['amount'],
                emissions=emissions,
            ))

        yield EmissionData(
            timestamp_utc=timestamp_utc,
            sector=sector,
            parts=parts,
        )


MixEmissionsData = NewType(
    name='MixEmissionsData',
    typ=List[EmissionData],
    field=marshmallow.fields.Function,
    deserialize=lambda mix_emissions: list(mix_emissions_to_emission_data(mix_emissions)),
)


@dataclass
class GetMixEmissionsResponse:
    success: bool
    mix_emissions: MixEmissionsData
