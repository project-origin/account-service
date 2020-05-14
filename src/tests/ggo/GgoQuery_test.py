import pytest
import testing.postgresql
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta, timezone
from itertools import product

from origin.db import ModelBase
from origin.auth import User, MeteringPoint
from origin.ggo.models import Ggo
from origin.ggo.queries import GgoQuery


GGO_AMOUNT = 100


user1 = User(
    id=1,
    sub='28a7240c-088e-4659-bd66-d76afb8c762f',
    access_token='access_token',
    refresh_token='access_token',
    token_expire=datetime(2030, 1, 1, 0, 0, 0),
    master_extended_key=(
        'xprv9s21ZrQH143K2CK5syo8PdeX5Y4TYFkcU'
        'KonHhm1e7znhaKj6odQFbbBa7T2Y77AtiNmU6'
        'aatP2qJBTwvhqxvaSBHA9hEfZ5gViAS3bBj7F'
    ),
)

user2 = User(
    id=2,
    sub='972cfd2e-cbd3-42e6-8e0e-c0c5c502f25f',
    access_token='access_token',
    refresh_token='access_token',
    token_expire=datetime(2030, 1, 1, 0, 0, 0),
    master_extended_key=(
        'xprv9s21ZrQH143K2CK5syo8PdeX5Y4TYFkcU'
        'KonHhm1e7znhaKj6odQFbbBa7T2Y77AtiNmU6'
        'aatP2qJBTwvhqxvaSBHA9hEfZ5gViAS3bBj7F'
    ),
)

meteringpoint1 = MeteringPoint(
    id=1,
    user=user1,
    gsrn='GSRN1',
    sector='DK1',
    key_index=0,
)

meteringpoint2 = MeteringPoint(
    id=2,
    user=user2,
    gsrn='GSRN2',
    sector='DK1',
    key_index=0,
)


def seed_ggo_test_data(session):

    # Dependencies
    session.add(user1)
    session.add(user2)
    session.add(meteringpoint1)
    session.add(meteringpoint2)

    # Input for combinations
    users = (user1, user2)
    issue_meteringpoints = (None, meteringpoint1, meteringpoint2)
    retire_meteringpoints = (None, meteringpoint1, meteringpoint2)
    issued = (True, False)
    stored = (True, False)
    retired = (True, False)
    synchronized = (True, False)
    locked = (True, False)
    sector = ('DK1', 'DK2')
    retire_address = (None, 'RETIRE-ADDRESS-1', 'RETIRE-ADDRESS-2')
    begin = (
        datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        datetime(2020, 1, 1, 1, 0, 0, tzinfo=timezone.utc),
        datetime(2020, 1, 2, 1, 0, 0, tzinfo=timezone.utc),
        datetime(2020, 2, 1, 1, 0, 0, tzinfo=timezone.utc),
        datetime(2021, 2, 1, 1, 0, 0, tzinfo=timezone.utc),
    )

    # Combinations
    combinations = product(
        users, issue_meteringpoints, retire_meteringpoints, retire_address,
        issued, stored, retired, synchronized, locked, sector, begin,
    )

    # Seed GGOs
    for i, (usr, iss_mp, ret_mp, ret_addr, iss,
            st, ret, sync, loc, sec, begin) in enumerate(combinations, start=1):

        session.add(Ggo(
            id=i,
            user=usr,
            address=str(i),
            issue_time=datetime(2020, 1, 1, 0, 0, 0),
            expire_time=datetime(2030, 1, 1, 0, 0, 0),
            begin=begin,
            end=begin + timedelta(hours=1),
            amount=GGO_AMOUNT,
            sector=sec,
            technology_code='T010000',
            fuel_code='F00000000',
            issued=iss,
            stored=st,
            retired=ret,
            synchronized=sync,
            locked=loc,
            issue_meteringpoint=iss_mp,
            retire_meteringpoint=ret_mp,
            retire_address=ret_addr,
        ))

        if i % 500 == 0:
            session.flush()


    session.commit()


@pytest.fixture(scope='module')
def seeded_session():
    """
    Returns a Session object with Ggo + User data seeded for testing
    """
    with testing.postgresql.Postgresql() as psql:
        engine = create_engine(psql.url())
        ModelBase.metadata.create_all(engine)
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        session = Session()

        seed_ggo_test_data(session)

        yield session

        session.close()


# -- TEST CASES --------------------------------------------------------------


@pytest.mark.parametrize('ggo_id', (1, 2))
def test__GgoQuery__has_id__Ggo_exists__returns_correct_Ggo(seeded_session, ggo_id):
    query = GgoQuery(seeded_session) \
        .has_id(ggo_id)

    assert query.count() == 1
    assert query.one().id == ggo_id


@pytest.mark.parametrize('ggo_id', (-1, 0))
def test__GgoQuery__has_id__Ggo_does_not_exist__returs_nothing(seeded_session, ggo_id):
    query = GgoQuery(seeded_session) \
        .has_id(ggo_id)

    assert query.count() == 0
    assert query.one_or_none() is None


@pytest.mark.parametrize('ggo_address', ('1', '2'))
def test__GgoQuery__has_address__Ggo_exists__returns_correct_Ggo(seeded_session, ggo_address):
    query = GgoQuery(seeded_session) \
        .has_address(ggo_address)

    assert query.count() == 1
    assert query.one().address == ggo_address


@pytest.mark.parametrize('ggo_address', ('asd', '0'))
def test__GgoQuery__has_address__Ggo_does_not_exist__returs_nothing(seeded_session, ggo_address):
    query = GgoQuery(seeded_session) \
        .has_address(ggo_address)

    assert query.count() == 0
    assert query.one_or_none() is None


def test__GgoQuery__belongs_to__returns_correct_ggos(seeded_session):
    query = GgoQuery(seeded_session) \
        .belongs_to(user1)

    assert query.count() > 0
    assert all(ggo.user_id == 1 for ggo in query.all())


@pytest.mark.parametrize('ggo_begin', (
        datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        datetime(2020, 1, 1, 1, 0, 0, tzinfo=timezone.utc),
        datetime(2020, 1, 2, 1, 0, 0, tzinfo=timezone.utc),
        datetime(2020, 2, 1, 1, 0, 0, tzinfo=timezone.utc),
        datetime(2021, 2, 1, 1, 0, 0, tzinfo=timezone.utc),
))
def test__GgoQuery__begins_at__returns_correct_ggos(seeded_session, ggo_begin):
    query = GgoQuery(seeded_session) \
        .begins_at(ggo_begin)

    assert query.count() > 0
    assert all(ggo.begin == ggo_begin for ggo in query.all())


@pytest.mark.parametrize('ggo_begin', (
        datetime(2030, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        datetime(2030, 1, 1, 1, 0, 0, tzinfo=timezone.utc),
        datetime(2030, 1, 2, 1, 0, 0, tzinfo=timezone.utc),
        datetime(2030, 2, 1, 1, 0, 0, tzinfo=timezone.utc),
        datetime(2031, 2, 1, 1, 0, 0, tzinfo=timezone.utc),
))
def test__GgoQuery__begins_at__Ggo_does_not_exist__returs_nothing(seeded_session, ggo_begin):
    query = GgoQuery(seeded_session) \
        .begins_at(ggo_begin)

    assert query.count() == 0


@pytest.mark.parametrize('ggo_issued', (True, False))
def test__GgoQuery__is_issued__returns_correct_ggos(seeded_session, ggo_issued):
    query = GgoQuery(seeded_session) \
        .is_issued(ggo_issued)

    assert query.count() > 0
    assert all(ggo.issued == ggo_issued for ggo in query.all())


@pytest.mark.parametrize('ggo_stored', (True, False))
def test__GgoQuery__is_stored__returns_correct_ggos(seeded_session, ggo_stored):
    query = GgoQuery(seeded_session) \
        .is_stored(ggo_stored)

    assert query.count() > 0
    assert all(ggo.stored == ggo_stored for ggo in query.all())


@pytest.mark.parametrize('ggo_retired', (True, False))
def test__GgoQuery__is_retired__returns_correct_ggos(seeded_session, ggo_retired):
    query = GgoQuery(seeded_session) \
        .is_retired(ggo_retired)

    assert query.count() > 0
    assert all(ggo.retired == ggo_retired for ggo in query.all())


@pytest.mark.parametrize('ggo_retire_address', ('RETIRE-ADDRESS-1', 'RETIRE-ADDRESS-2'))
def test__GgoQuery__is_retired_to_address__returns_correct_ggos(seeded_session, ggo_retire_address):
    query = GgoQuery(seeded_session) \
        .is_retired_to_address(ggo_retire_address)

    assert query.count() > 0
    assert all(ggo.retired is True for ggo in query.all())
    assert all(ggo.retire_gsrn is not None for ggo in query.all())
    assert all(ggo.retire_address == ggo_retire_address for ggo in query.all())


@pytest.mark.parametrize('ggo_retire_gsrn', ('GSRN1', 'GSRN2'))
def test__GgoQuery__is_retired_to_gsrn__returns_correct_ggos(seeded_session, ggo_retire_gsrn):
    query = GgoQuery(seeded_session) \
        .is_retired_to_gsrn(ggo_retire_gsrn)

    assert query.count() > 0
    assert all(ggo.retired is True for ggo in query.all())
    assert all(ggo.retire_address is not None for ggo in query.all())
    assert all(ggo.retire_gsrn == ggo_retire_gsrn for ggo in query.all())


# TODO is_expired


@pytest.mark.parametrize('ggo_synchronized', (True, False))
def test__GgoQuery__is_synchronized__returns_correct_ggos(seeded_session, ggo_synchronized):
    query = GgoQuery(seeded_session) \
        .is_synchronized(ggo_synchronized)

    assert query.count() > 0
    assert all(ggo.synchronized == ggo_synchronized for ggo in query.all())


@pytest.mark.parametrize('ggo_locked', (True, False))
def test__GgoQuery__is_locked__returns_correct_ggos(seeded_session, ggo_locked):
    query = GgoQuery(seeded_session) \
        .is_locked(ggo_locked)

    assert query.count() > 0
    assert all(ggo.locked == ggo_locked for ggo in query.all())


def test__GgoQuery__is_tradable__returns_correct_ggos(seeded_session):
    query = GgoQuery(seeded_session) \
        .is_tradable()

    assert query.count() > 0
    assert all(ggo.stored is True for ggo in query.all())
    # assert all(ggo.expired is False for ggo in query.all())
    assert all(ggo.retired is False for ggo in query.all())

    assert all(ggo.synchronized is True for ggo in query.all())
    assert all(ggo.locked is False for ggo in query.all())


def test__GgoQuery__get_total_amount__has_results__returns_correct_amount(seeded_session):
    query = GgoQuery(seeded_session)

    assert query.count() > 0
    assert query.get_total_amount() == query.count() * GGO_AMOUNT


def test__GgoQuery__get_total_amount__has_no_results__returns_zero(seeded_session):
    query = GgoQuery(seeded_session) \
        .has_address('AN-ADDRESS-THAT-DOESNT-EXISTS')

    assert query.count() == 0
    assert query.get_total_amount() == 0


def test__GgoQuery__get_distinct_begins__has_results__returns_list_of_correct_begins(seeded_session):
    query = GgoQuery(seeded_session)
    distinct_begins = query.get_distinct_begins()

    assert len(distinct_begins) == 5
    assert sorted(distinct_begins) == [
        datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        datetime(2020, 1, 1, 1, 0, 0, tzinfo=timezone.utc),
        datetime(2020, 1, 2, 1, 0, 0, tzinfo=timezone.utc),
        datetime(2020, 2, 1, 1, 0, 0, tzinfo=timezone.utc),
        datetime(2021, 2, 1, 1, 0, 0, tzinfo=timezone.utc),
    ]


def test__GgoQuery__get_distinct_begins__has_no_results__returns_empty_list(seeded_session):
    query = GgoQuery(seeded_session) \
        .has_address('AN-ADDRESS-THAT-DOESNT-EXISTS')

    assert query.count() == 0
    assert query.get_distinct_begins() == []
