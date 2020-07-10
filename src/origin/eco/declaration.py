import operator
from itertools import groupby
from typing import Dict
from datetime import datetime
from dataclasses import dataclass

from .models import EcoDeclarationResolution


class EmissionValues(dict):
    """
    TODO
    """

    def __repr__(self):
        return 'EmissionValues<%s>' % super(EmissionValues, self).__repr__()

    def add(self, key, value):
        self.setdefault(key, 0)
        self[key] += value

    def __add__(self, other):
        """
        :param EmissionValues|int|float other:
        :rtype: EmissionValues
        """
        return self.__do_arithmetic(other, operator.__add__)

    def __radd__(self, other):
        """
        :param EmissionValues|int|float other:
        :rtype: EmissionValues
        """
        return self + other

    def __mul__(self, other):
        """
        :param EmissionValues|int|float other:
        :rtype: EmissionValues
        """
        return self.__do_arithmetic(other, operator.__mul__)

    def __rmul__(self, other):
        """
        :param EmissionValues|int|float other:
        :rtype: EmissionValues
        """
        return self * other

    def __truediv__(self, other):
        """
        :param EmissionValues|int|float other:
        :rtype: EmissionValues
        """
        return self.__do_arithmetic(other, operator.__truediv__)

    def __do_arithmetic(self, other, calc):
        """
        :param EmissionValues|int|float other:
        :param function calc:
        :rtype: EmissionValues
        """
        if isinstance(other, dict):
            keys = set(list(self.keys()) + list(other.keys()))
            return EmissionValues(
                **{key: calc(self.get(key, 0), other.get(key, 0))
                   for key in keys}
            )
        elif isinstance(other, (int, float)):
            return EmissionValues(
                **{key: calc(self.get(key, 0), other)
                   for key in self.keys()}
            )

        return NotImplemented


@dataclass
class EcoDeclaration:
    """
    TODO
    """

    # Emission in gram (mapped by begin)
    emissions: Dict[datetime, EmissionValues]

    # Energy consumption in Wh (mapped by begin)
    consumed_amount: Dict[datetime, int]

    # Current resolution
    resolution: EcoDeclarationResolution

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
        return sum(self.emissions.values())

    @property
    def emissions_per_wh(self):
        """
        Returns the emissions in gram/Wh.

        :rtype: dict[datetime, EmissionValues]
        """
        result = {}

        for begin in self.emissions:
            if self.consumed_amount[begin] > 0:
                result[begin] = self.emissions[begin] / self.consumed_amount[begin]
            else:
                result[begin] = 0

        return result

    @property
    def total_emissions_per_wh(self):
        """
        Returns the total emissions in gram/Wh (aggregated for all begins).

        :rtype: EmissionValues
        """
        consumed_amount = self.total_consumed_amount

        if consumed_amount > 0:
            return sum(self.emissions.values()) / consumed_amount
        else:
            return EmissionValues()

    def as_resolution(self, resolution):
        """
        :param EcoDeclarationResolution resolution:
        :rtype: EcoDeclaration
        """
        if resolution == self.resolution:
            return self
        if resolution > self.resolution:
            raise ValueError((
                'Can not get declaration in higher resolution than the '
                'source data is represented in'
            ))

        mappers = {
            EcoDeclarationResolution.day: lambda d: d.replace(
                hour=0, minute=0, second=0, microsecond=0),

            EcoDeclarationResolution.month: lambda d: d.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0),

            EcoDeclarationResolution.year: lambda d: d.replace(
                month=1, day=1, hour=0, minute=0, second=0, microsecond=0),
        }

        begins_sorted_and_grouped = groupby(
            iterable=sorted(self.emissions.keys()),
            key=mappers[resolution],
        )

        new_emissions = {}
        new_consumed_amount = {}

        for new_begin, old_begins in begins_sorted_and_grouped:
            old_begins = list(old_begins)
            new_emissions[new_begin] = sum(self.emissions[b] for b in old_begins)
            new_consumed_amount[new_begin] = sum(self.consumed_amount[b] for b in old_begins)

        return EcoDeclaration(
            emissions=new_emissions,
            consumed_amount=new_consumed_amount,
            resolution=resolution,
        )
