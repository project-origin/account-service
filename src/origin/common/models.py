from datetime import datetime
from dataclasses import dataclass
from marshmallow import validates_schema, ValidationError


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
