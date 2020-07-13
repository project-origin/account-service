from datetime import datetime
from dataclasses import dataclass
from marshmallow import validates_schema, ValidationError


@dataclass
class DateTimeRange:
    begin: datetime
    end: datetime

    @validates_schema
    def validate_input(self, data, **kwargs):
        if data['begin'].utcoffset() != data['end'].utcoffset():
            raise ValidationError({
                'begin': ['Must have same time offset as end'],
                'end': ['Must have same time offset as begin'],
            })

        if data['begin'] > data['end']:
            raise ValidationError({
                'begin': ['Must be before end'],
                'end': ['Must be after begin'],
            })
