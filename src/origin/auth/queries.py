from datetime import datetime, timezone

from sqlalchemy.orm import raiseload

from origin.settings import TOKEN_REFRESH_AT

from .models import User, MeteringPoint


class UserQuery(object):
    """
    TODO
    """
    def __init__(self, session, q=None):
        """
        :param Session session:
        :param Query q:
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
        :param int id:
        :rtype: UserQuery
        """
        return UserQuery(self.session, self.q.filter(
            User.id == id,
        ))

    def has_sub(self, sub):
        """
        :param str sub:
        :rtype: UserQuery
        """
        return UserQuery(self.session, self.q.filter(
            User.sub == sub,
        ))

    def has_gsrn(self, gsrn):
        """
        :param str gsrn:
        :rtype: UserQuery
        """
        return UserQuery(self.session, self.q.filter(
            User.metering_points.any(gsrn=gsrn),
        ))

    def should_refresh_token(self):
        """
        :rtype: UserQuery
        """
        return UserQuery(self.session, self.q.filter(
            User.token_expire <= datetime.now(tz=timezone.utc) + TOKEN_REFRESH_AT,
        ))


class MeteringPointQuery(object):
    """
    TODO
    """
    def __init__(self, session, q=None):
        """
        :param Session session:
        :param Query q:
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
        TODO

        :param User user:
        :rtype: MeteringPointQuery
        """
        return self.__class__(self.session, self.q.filter(
            MeteringPoint.user_id == user.id,
        ))

    def has_gsrn(self, gsrn):
        """
        :param str gsrn:
        :rtype: MeteringPointQuery
        """
        return MeteringPointQuery(self.session, self.q.filter(
            MeteringPoint.gsrn == gsrn,
        ))
