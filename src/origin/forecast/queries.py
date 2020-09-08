import sqlalchemy as sa
from datetime import datetime, timezone

from origin.auth import User

from .models import Forecast


class ForecastQuery(object):
    """
    TODO
    """
    def __init__(self, session, q=None):
        """
        :param sa.orm.Session session:
        :param sa.orm.Query q:
        """
        self.session = session
        if q is not None:
            self.q = q
        else:
            self.q = session.query(Forecast)

    def __iter__(self):
        return iter(self.q)

    def __getattr__(self, name):
        return getattr(self.q, name)

    def has_id(self, id):
        """
        Only include the Forecasts with a specific ID.

        :param int id:
        :rtype: ForecastQuery
        """
        return self.__class__(self.session, self.q.filter(
            Forecast.id == id,
        ))

    def has_public_id(self, public_id):
        """
        Only include the Forecasts with a specific ID.

        :param str public_id:
        :rtype: ForecastQuery
        """
        return self.__class__(self.session, self.q.filter(
            Forecast.public_id == public_id,
        ))

    def has_reference(self, reference):
        """
        Only include the Forecasts with a specific reference.

        :param str reference:
        :rtype: ForecastQuery
        """
        return self.__class__(self.session, self.q.filter(
            Forecast.reference == reference,
        ))

    def is_sent_by(self, user):
        """
        Only include Forecasts which were sent by a specific user.

        :param User user:
        :rtype: ForecastQuery
        """
        return self.__class__(self.session, self.q.filter(
            Forecast.user_id == user.id,
        ))

    def is_received_by(self, user):
        """
        Only include Forecasts which were received by a specific user.

        :param User user:
        :rtype: ForecastQuery
        """
        return self.__class__(self.session, self.q.filter(
            Forecast.recipient_id == user.id,
        ))

    def is_sent_or_received_by(self, user):
        """
        Only include Forecasts which were sent or received by a specific user.

        :param User user:
        :rtype: ForecastQuery
        """
        return self.__class__(self.session, self.q.filter(
            sa.or_(
                Forecast.user_id == user.id,
                Forecast.recipient_id == user.id,
            )
        ))

    def at_time(self, dt):
        """
        Only include Forecasts which includes forecasts at a specific time.

        :param datetime dt:
        :rtype: ForecastQuery
        """
        return self.__class__(self.session, self.q.filter(
            sa.and_(
                Forecast.begin <= dt.astimezone(timezone.utc),
                Forecast.end >= dt.astimezone(timezone.utc),
            )
        ))

    def get_distinct_references(self):
        """
        Returns a list of all distinct references in the result set.

        :rtype: list[str]
        """
        return [row[0] for row in self.session.query(
            self.q.subquery().c.reference.distinct())]
