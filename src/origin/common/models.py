from dataclasses import dataclass
from datetime import datetime, date
from marshmallow import validates_schema, ValidationError


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

    @property
    def delta(self):
        """
        :rtype: timedelta
        """
        return self.end - self.begin


@dataclass
class DateTimeRange:
    begin: datetime
    end: datetime

    @classmethod
    def from_date_range(cls, date_range):
        """
        :param DateRange date_range:
        :rtype: DateTimeRange
        """
        return DateTimeRange(
            begin=datetime.fromordinal(date_range.begin.toordinal()),
            end=datetime.fromordinal(date_range.end.toordinal()).replace(hour=23, minute=59, second=59),
            # end=datetime.fromordinal(date_range.end.toordinal()) + timedelta(days=1),
        )

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
