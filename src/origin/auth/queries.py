from sqlalchemy.orm import raiseload
from datetime import datetime, timezone

from origin.settings import TOKEN_REFRESH_AT

from .models import User, MeteringPoint


class UserQuery(object):
    """
    Abstraction around querying User objects from the database,
    supporting cascade calls to combine filters.

    Usage example::

        query = UserQuery(session) \
            .has_gsrn('123456789012345') \
            .should_refresh_token()

        for user in query:
            pass

    Attributes not present on the UserQuery class is redirected to
    SQLAlchemy's Query object, like count(), all() etc., for example::

        query = UserQuery(session) \
            .has_gsrn('123456789012345') \
            .should_refresh_token() \
            .offset(100) \
            .limit(20) \
            .count()

    """
    def __init__(self, session, q=None):
        """
        :param sqlalchemy.orm.Session session:
        :param sqlalchemy.orm.Query q:
        """
        self.session = session
        if q is None:
            self.q = session.query(User).options(raiseload(User.metering_points))
        else:
            self.q = q

    def __iter__(self):
        return iter(self.q)

    def __getattr__(self, name):
        return getattr(self.q, name)

    def has_id(self, id):
        """
        Only include the user with a specific ID.

        :param int id:
        :rtype: UserQuery
        """
        return UserQuery(self.session, self.q.filter(
            User.id == id,
        ))

    def has_sub(self, sub):
        """
        Only include the user with a specific subject.

        :param str sub:
        :rtype: UserQuery
        """
        return UserQuery(self.session, self.q.filter(
            User.sub == sub,
        ))

    def has_gsrn(self, gsrn):
        """
        Only include users which owns the MeteringPoint identified with
        the provided GSRN number.

        :param str gsrn:
        :rtype: UserQuery
        """
        return UserQuery(self.session, self.q.filter(
            User.metering_points.any(gsrn=gsrn),
        ))

    def should_refresh_token(self):
        """
        Only include users which should have their tokens refreshed.

        :rtype: UserQuery
        """
        return UserQuery(self.session, self.q.filter(
            User.token_expire <= datetime.now(tz=timezone.utc) + TOKEN_REFRESH_AT,
        ))


class MeteringPointQuery(object):
    """
    Abstraction around querying MeteringPoint objects from the database,
    supporting cascade calls to combine filters.

    Usage example::

        query = MeteringPointQuery(session) \
            .belongs_to(user) \
            .has_gsrn('123456789012345')

        for meteringpoint in query:
            pass

    Attributes not present on the UserQuery class is redirected to
    SQLAlchemy's Query object, like count(), all() etc., for example::

        query = MeteringPointQuery(session) \
            .belongs_to(user) \
            .has_gsrn('123456789012345') \
            .offset(100) \
            .limit(20) \
            .count()

    """
    def __init__(self, session, q=None):
        """
        :param sqlalchemy.orm.Session session:
        :param sqlalchemy.orm.Query q:
        """
        self.session = session
        if q is None:
            self.q = session.query(MeteringPoint)
        else:
            self.q = q

    def __iter__(self):
        return iter(self.q)

    def __getattr__(self, name):
        return getattr(self.q, name)

    def belongs_to(self, user):
        """
        Only include meteringpoints which belong to the provided user.

        :param User user:
        :rtype: MeteringPointQuery
        """
        return self.__class__(self.session, self.q.filter(
            MeteringPoint.user_id == user.id,
        ))

    def has_gsrn(self, gsrn):
        """
        Only include the meteringpoint with the provided GSRN number.

        :param str gsrn:
        :rtype: MeteringPointQuery
        """
        return MeteringPointQuery(self.session, self.q.filter(
            MeteringPoint.gsrn == gsrn,
        ))
