import operator
from datetime import datetime
from typing import List, Dict
from dataclasses import dataclass, field


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
