from itertools import groupby
from datetime import datetime, timezone, timedelta

from origin.common import EmissionValues

from .models import EcoDeclarationResolution


class EcoDeclaration(object):
    """
    TODO
    """

    @classmethod
    def empty(cls):
        """
        :rtype: EcoDeclaration
        """
        return cls(
            emissions={},
            consumed_amount={},
            technologies={},
            resolution=EcoDeclarationResolution.hour,
            utc_offset=0,
        )

    def __init__(self, emissions, consumed_amount,
                 technologies, resolution, utc_offset):
        """
        :param dict[datetime, EmissionValues[str, float]] emissions:
            Emissions in gram
        :param dict[datetime, float] consumed_amount:
            Dict of {begin: amount}
        :param dict[datetime, EmissionValues[str, float]] technologies:
            Dict of {technology: amount}
        :param EcoDeclarationResolution resolution:
        :param int utc_offset:
        """
        if not isinstance(emissions, dict):  # TODO test this
            raise ValueError('emissions must be of type dict')
        if not all(isinstance(v, EmissionValues) for v in emissions.values()):
            raise ValueError('All values of emissions must be of type EmissionValues')

        if not isinstance(consumed_amount, dict):
            raise ValueError('consumed_amount must be of type dict')

        if not isinstance(technologies, dict):  # TODO test this
            raise ValueError('technologies must be of type dict')
        if not all(isinstance(v, EmissionValues) for v in technologies.values()):
            raise ValueError('All values of technologies must be of type EmissionValues')

        if sorted(technologies.keys()) != sorted(consumed_amount.keys()):
            raise ValueError('technologies and consumed_amount should have the same keys')
        if not all(round(sum(technologies[k].values())) == round(consumed_amount[k]) for k in consumed_amount):
            raise ValueError('Sum of technologies must be equal to sum of consumed amount')

        if sorted(emissions.keys()) != sorted(consumed_amount.keys()):
            raise ValueError((
                'Arguments "emissions" and "consumed_amount" must have '
                'exactly the same keys (begins)'
            ))

        # Make sure all EmissionValues dicts has all of the same keys
        # with None as default
        unique_keys = set(k for d in emissions.values() for k in d.keys())
        for k, v in emissions.items():
            for u in unique_keys:
                v.setdefault(u, None)

        self.emissions = emissions
        self.consumed_amount = consumed_amount
        self.technologies = technologies
        self.resolution = resolution
        self.utc_offset = utc_offset

    @property
    def total_consumed_amount(self):
        """
        TODO

        :rtype: int
        """
        return sum(self.consumed_amount.values())

    @property
    def total_emissions(self):
        """
        Returns the total emissions in gram/Wh (aggregated for all begins).

        :rtype: EmissionValues
        """
        return sum(self.emissions.values(), EmissionValues())

    @property
    def total_technologies(self):
        """
        TODO
        TODO test this

        :rtype: EmissionValues
        """
        return sum(self.technologies.values(), EmissionValues())

    @property
    def technologies_percentage(self):
        """
        Returns technologies as percent of total consumption.

        :rtype: EmissionValues
        """
        return self.total_technologies / self.total_consumed_amount * 100

    @property
    def emissions_per_wh(self):
        """
        Returns the emissions in gram/Wh.

        :rtype: dict[datetime, EmissionValues]
        """
        emissions = {}

        for begin in self.emissions:
            if self.consumed_amount[begin] > 0:
                emissions[begin] = self.emissions[begin] / self.consumed_amount[begin]
            else:
                emissions[begin] = self.emissions[begin] * 0

        return emissions

    @property
    def total_emissions_per_wh(self):
        """
        Returns the total emissions in gram/Wh (aggregated for all begins).

        :rtype: EmissionValues
        """
        consumed_amount = self.total_consumed_amount

        if consumed_amount > 0:
            return self.total_emissions / consumed_amount
        else:
            return EmissionValues()

    def as_resolution(self, resolution, utc_offset):
        """
        :param EcoDeclarationResolution resolution:
        :param int utc_offset:
        :rtype: EcoDeclaration
        """
        if (resolution, utc_offset) == (self.resolution, self.utc_offset):
            return self
        if resolution > self.resolution:
            raise ValueError((
                'Can not get declaration in higher resolution than the '
                'source data is represented in'
            ))

        mappers = {
            EcoDeclarationResolution.year: lambda d: d.replace(
                month=1, day=1, hour=0, minute=0, second=0, microsecond=0),
            EcoDeclarationResolution.month: lambda d: d.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0),
            EcoDeclarationResolution.day: lambda d: d.replace(
                hour=0, minute=0, second=0, microsecond=0),
            EcoDeclarationResolution.hour: lambda d: d.replace(
                minute=0, second=0, microsecond=0),
        }

        def __map_utc_offset(begin):
            """
            :param datetime begin:
            :rtype: datetime
            """
            return begin.astimezone(timezone(timedelta(hours=utc_offset)))

        begins = self.emissions.keys()

        if utc_offset != self.utc_offset:
            begins = map(__map_utc_offset, begins)

        begins_sorted_and_grouped = groupby(
            iterable=sorted(begins),
            key=mappers[resolution],
        )

        new_emissions = {}
        new_consumed_amount = {}
        new_technologies = {}

        for new_begin, old_begins in begins_sorted_and_grouped:
            old_begins = list(old_begins)
            # TODO start=EmissionValues()
            new_emissions[new_begin] = \
                sum(self.emissions[b] for b in old_begins)

            new_consumed_amount[new_begin] = \
                sum(self.consumed_amount[b] for b in old_begins)

            new_technologies[new_begin] = \
                sum(self.technologies[b] for b in old_begins)

        return EcoDeclaration(
            emissions=new_emissions,
            consumed_amount=new_consumed_amount,
            resolution=resolution,
            technologies=new_technologies,
            utc_offset=utc_offset,
        )
