from enum import Enum
from datetime import date, datetime
from dataclasses import dataclass
from marshmallow import validates_schema, ValidationError


class Unit(Enum):
    Wh = 1
    KWh = 10**3
    MWh = 10**6
    GWh = 10**9


@dataclass
class DateRange:
    begin: date
    end: date

    @validates_schema
    def validate_begin_before_end(self, data, **kwargs):
        if data['begin'] > data['end']:
            raise ValidationError({
                'begin': ['Must be before end'],
                'end': ['Must be after begin'],
            })


@dataclass
class DateTimeRange:
    begin: datetime
    end: datetime

    @validates_schema
    def validate_begin_before_end(self, data, **kwargs):
        if data['begin'] > data['end']:
            raise ValidationError({
                'begin': ['Must be before end'],
                'end': ['Must be after begin'],
            })


