import sqlalchemy as sa
from sqlalchemy import func, bindparam
from sqlalchemy.orm import aliased
from datetime import datetime
from itertools import groupby
from functools import lru_cache
from dateutil.relativedelta import relativedelta

from origin.auth import User
from origin.common import DateTimeRange
from origin.ledger import SplitTarget, SplitTransaction

from .models import (
    Ggo,
    SummaryGroup,
    GgoFilters,
    GgoCategory,
    SummaryResolution,
    RetireFilters,
)


class GgoQuery(object):
    """
    TODO
    """
    def __init__(self, session, q=None):
        """
        :param Session session:
        :param Query q:
        """
        self.session = session
        if q is not None:
            self.q = q
        else:
            self.q = session.query(Ggo)

    def __iter__(self):
        return iter(self.q)

    def __getattr__(self, name):
        return getattr(self.q, name)

    def apply_filters(self, filters):
        """
        :param GgoFilters filters:
        :rtype: GgoQuery
        """
        q = self.q

        if filters.begin:
            q = q.filter(Ggo.begin == filters.begin)
        elif filters.begin_range:
            q = q.filter(Ggo.begin >= filters.begin_range.begin)
            q = q.filter(Ggo.begin <= filters.begin_range.end)
        if filters.sector:
            q = q.filter(Ggo.sector.in_(filters.sector))
        if filters.technology_code:
            q = q.filter(Ggo.technology_code.in_(filters.technology_code))
        if filters.fuel_code:
            q = q.filter(Ggo.fuel_code.in_(filters.fuel_code))
        if filters.issue_gsrn:
            q = q.filter(Ggo.issue_gsrn.in_(filters.issue_gsrn))
        if filters.retire_gsrn:
            q = q.filter(Ggo.retire_gsrn.in_(filters.retire_gsrn))

        new_query = self.__class__(self.session, q)

        if filters.category == GgoCategory.ISSUED:
            new_query = new_query.is_issued(True)
        elif filters.category == GgoCategory.STORED:
            new_query = new_query.is_stored(True).is_expired(False)
        elif filters.category == GgoCategory.RETIRED:
            new_query = new_query.is_retired(True)
        elif filters.category == GgoCategory.EXPIRED:
            new_query = new_query.is_stored(True).is_expired(True)

        return new_query

    def has_id(self, id):
        """
        TODO

        :param int id:
        :rtype: GgoQuery
        """
        return self.__class__(self.session, self.q.filter(
            Ggo.id == id,
        ))

    def has_address(self, address):
        """
        TODO

        :param str address:
        :rtype: GgoQuery
        """
        return self.__class__(self.session, self.q.filter(
            Ggo.address == address,
        ))

    def belongs_to(self, user):
        """
        TODO

        :param User user:
        :rtype: GgoQuery
        """
        return self.__class__(self.session, self.q.filter(
            Ggo.user_id == user.id,
        ))

    def begins_at(self, begin):
        """
        TODO

        :param datetime begin:
        :rtype: GgoQuery
        """
        return self.__class__(self.session, self.q.filter(
            Ggo.begin == begin,
        ))

    def is_issued(self, value):
        """
        TODO

        :param bool value:
        :rtype: GgoQuery
        """
        return self.__class__(self.session, self.q.filter(
            Ggo.issued.is_(value),
        ))

    def is_stored(self, value):
        """
        TODO

        :param bool value:
        :rtype: GgoQuery
        """
        return self.__class__(self.session, self.q.filter(
            Ggo.stored.is_(value),
        ))

    def is_retired(self, value):
        """
        TODO

        :param bool value:
        :rtype: GgoQuery
        """
        return self.__class__(self.session, self.q.filter(
            Ggo.retired.is_(value),
        ))

    def is_retired_to_address(self, address):
        """
        TODO

        :param str address:
        :rtype: GgoQuery
        """
        return self.__class__(self.session, self.q.filter(
            Ggo.retired.is_(True),
            Ggo.retire_address == address,
        ))

    def is_retired_to_gsrn(self, gsrn):
        """
        TODO

        :param str gsrn:
        :rtype: GgoQuery
        """
        return self.__class__(self.session, self.q.filter(
            Ggo.retired.is_(True),
            Ggo.retire_gsrn == gsrn,
        ))

    def is_expired(self, value):
        """
        TODO

        :param bool value:
        :rtype: GgoQuery
        """
        if value is True:
            cond = Ggo.expire_time <= sa.func.now()
        elif value is False:
            cond = Ggo.expire_time > sa.func.now()
        else:
            raise RuntimeError('Should NOT have happened!')

        return self.__class__(self.session, self.q.filter(cond))

    def is_synchronized(self, value):
        """
        TODO

        :param bool value:
        :rtype: GgoQuery
        """
        return self.__class__(self.session, self.q.filter(
            Ggo.synchronized.is_(value),
        ))

    def is_locked(self, value):
        """
        TODO

        :param bool value:
        :rtype: GgoQuery
        """
        return self.__class__(self.session, self.q.filter(
            Ggo.locked.is_(value),
        ))

    def is_tradable(self):
        """
        TODO

        :rtype: GgoQuery
        """
        return self \
            .is_stored(True) \
            .is_expired(False) \
            .is_retired(False) \
            .is_synchronized(True) \
            .is_locked(False)

    def is_retirable(self):
        """
        TODO

        :rtype: GgoQuery
        """
        return self.is_tradable()

    def is_eligible_to_retire(self, measurement):
        """
        TODO

        :param Measurement measurement:
        :rtype: GgoQuery
        """
        return self.__class__(self.session, self.q.filter(
            Ggo.begin == measurement.begin,
            Ggo.sector == measurement.sector,
        ))

    def get_total_amount(self):
        """
        :rtype: int
        """
        total_amount = self.session.query(
            func.sum(self.q.subquery().c.amount)).one()[0]
        return total_amount if total_amount is not None else 0

    def get_distinct_begins(self):
        """
        Returns an iterable of all distinct Ggo.begin
        as a result of this query.

        :rtype: list[datetime]
        """
        return [row[0] for row in self.session.query(
            self.q.subquery().c.begin.distinct())]

    def get_summary(self, resolution, grouping):
        """
        :param SummaryResolution resolution:
        :param list[str] grouping:
        :rtype: GgoSummary
        """
        return GgoSummary(self.session, self, resolution, grouping)


class TransactionQuery(GgoQuery):
    """
    TODO
    """

    parent_ggo = aliased(Ggo, name='parent')

    def __init__(self, session, q=None):
        """
        :param Session session:
        :param Query q:
        """
        if q is None:
            q = session.query(Ggo) \
                .join(SplitTarget, SplitTarget.ggo_id == Ggo.id) \
                .join(SplitTransaction, SplitTransaction.id == SplitTarget.transaction_id) \
                .join(self.parent_ggo, self.parent_ggo.id == SplitTransaction.parent_ggo_id) \
                .filter(Ggo.user_id != self.parent_ggo.user_id)

        super(TransactionQuery, self).__init__(session, q)

    def sent_by_user(self, user):
        """
        TODO

        :param User user:
        :rtype: TransactionQuery
        """
        return self.__class__(self.session, self.q.filter(
            self.parent_ggo.user_id == user.id,
        ))

    def received_by_user(self, user):
        """
        TODO

        :param User user:
        :rtype: TransactionQuery
        """
        return self.__class__(self.session, self.q.filter(
            Ggo.user_id == user.id,
        ))

    def sent_or_received_by_user(self, user):
        """
        TODO

        :param User user:
        :rtype: TransactionQuery
        """
        return self.__class__(self.session, self.q.filter(sa.or_(
            self.parent_ggo.user_id == user.id,
            Ggo.user_id == user.id,
        )))

    def apply_filters(self, filters):
        """
        :param TransferFilters filters:
        """
        q = super(TransactionQuery, self) \
            .apply_filters(filters)

        if filters.reference:
            q = q.has_any_reference(filters.reference)

        return q

    def has_reference(self, reference):
        """
        :param str reference:
        :rtype: TransactionQuery
        """
        return self.__class__(self.session, self.q.filter(
            SplitTarget.reference == reference,
        ))

    def has_any_reference(self, references):
        """
        :param list[str] references:
        :rtype: TransactionQuery
        """
        return self.__class__(self.session, self.q.filter(
            SplitTarget.reference.in_(references),
        ))


class RetireQuery(GgoQuery):
    """
    TODO
    """
    def __init__(self, session, q=None):
        """
        :param Session session:
        :param Query q:
        """
        super(RetireQuery, self).__init__(session, q)

        if q is None:
            self.q = self.q.filter(Ggo.retired.is_(True))

    def apply_filters(self, filters):
        """
        :param RetireFilters filters:
        """
        q = super(RetireQuery, self).apply_filters(filters).q

        if filters.gsrn:
            q = q.filter(Ggo.retire_gsrn.in_(filters.gsrn))
        if filters.address:
            q = q.filter(Ggo.retire_address.in_(filters.address))

        return self.__class__(self.session, q)


class GgoSummary(object):
    """
    TODO Describe
    """

    GROUPINGS = (
        'begin',
        'sector',
        'technologyCode',
        'fuelCode',
    )

    RESOLUTIONS_POSTGRES = {
        SummaryResolution.HOUR: 'YYYY-MM-DD HH24:00',
        SummaryResolution.DAY: 'YYYY-MM-DD',
        SummaryResolution.MONTH: 'YYYY-MM',
        SummaryResolution.YEAR: 'YYYY',
    }

    RESOLUTIONS_PYTHON = {
        SummaryResolution.HOUR: '%Y-%m-%d %H:00',
        SummaryResolution.DAY: '%Y-%m-%d',
        SummaryResolution.MONTH: '%Y-%m',
        SummaryResolution.YEAR: '%Y',
    }

    LABEL_STEP = {
        SummaryResolution.HOUR: relativedelta(hours=1),
        SummaryResolution.DAY: relativedelta(days=1),
        SummaryResolution.MONTH: relativedelta(months=1),
        SummaryResolution.YEAR: relativedelta(years=1),
        SummaryResolution.ALL: None,
    }

    ALL_TIME_LABEL = 'All-time'

    def __init__(self, session, query, resolution, grouping):
        """
        :param Session session:
        :param GgoQuery query:
        :param SummaryResolution resolution:
        :param list[str] grouping:
        """
        self.session = session
        self.query = query
        self.resolution = resolution
        self.grouping = grouping
        self.fill_range = None

    def fill(self, fill_range):
        """
        :param DateTimeRange fill_range:
        """
        self.fill_range = fill_range

    @property
    def labels(self):
        """
        :rtype list[str]:
        """
        if self.resolution == SummaryResolution.ALL:
            return [self.ALL_TIME_LABEL]
        if self.fill_range is None:
            return sorted(set(label for label, *g, amount in self.raw_results))
        else:
            format = self.RESOLUTIONS_PYTHON[self.resolution]
            step = self.LABEL_STEP[self.resolution]
            begin = self.fill_range.begin
            labels = []

            while begin <= self.fill_range.end:
                labels.append(begin.strftime(format))
                begin += step

            return labels

    @property
    def groups(self):
        """
        :rtype list[SummaryGroup]:
        """
        groups = []

        for group, results in groupby(self.raw_results, lambda x: x[1:-1]):
            items = {label: amount for label, *g, amount in results}
            groups.append(SummaryGroup(
                group=group,
                values=[items.get(label, None) for label in self.labels],
            ))

        return groups

    @property
    @lru_cache()
    def raw_results(self):
        """
        TODO
        """
        select = []
        groups = []
        orders = []

        q = self.query.subquery()

        # -- Resolution ------------------------------------------------------

        if self.resolution == SummaryResolution.ALL:
            select.append(bindparam('label', self.ALL_TIME_LABEL))
        else:
            select.append(func.to_char(q.c.begin, self.RESOLUTIONS_POSTGRES[self.resolution]).label('resolution'))
            groups.append('resolution')

        # -- Grouping ------------------------------------------------------------

        for group in self.grouping:
            if group == 'begin':
                groups.append(q.c.begin)
                select.append(q.c.begin)
                orders.append(q.c.begin)
            elif group == 'sector':
                groups.append(q.c.sector)
                select.append(q.c.sector)
                orders.append(q.c.sector)
            elif group == 'technologyCode':
                groups.append(q.c.technology_code)
                select.append(q.c.technology_code)
                orders.append(q.c.technology_code)
            elif group == 'fuelCode':
                groups.append(q.c.fuel_code)
                select.append(q.c.fuel_code)
                orders.append(q.c.fuel_code)
            else:
                raise RuntimeError('Invalid grouping: %s' % self.grouping)

        # -- Query ---------------------------------------------------------------

        select.append(func.sum(q.c.amount))

        return self.session \
            .query(*select) \
            .group_by(*groups) \
            .order_by(*orders) \
            .all()
