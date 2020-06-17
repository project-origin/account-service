import pytest
import testing.postgresql
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta, timezone
from itertools import product

from origin.db import ModelBase
from origin.auth import User, MeteringPoint
from origin.ggo import Ggo, GgoQuery, Technology

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
    session.add(Technology(
        technology='Solar',
        technology_code='T010101',
        fuel_code='F01010101',
    ))
    session.add(Technology(
        technology='Wind',
        technology_code='T020202',
        fuel_code='F02020202',
    ))

    session.add(Ggo(
        id=1,
        user=user1,
        address='1',
        issue_time=datetime(2020, 1, 1, 0, 0, 0),
        expire_time=datetime(2030, 1, 1, 0, 0, 0),
        begin=datetime(2020, 1, 1, 0, 0, 0),
        end=datetime(2020, 1, 1, 1, 0, 0),
        amount=100,
        sector='DK1',
        technology_code='T010101',
        fuel_code='F01010101',
        issued=False,
        stored=False,
        retired=False,
        synchronized=False,
        locked=False,
    ))

    session.add(Ggo(
        id=2,
        user=user1,
        address='2',
        issue_time=datetime(2020, 1, 1, 0, 0, 0),
        expire_time=datetime(2030, 1, 1, 0, 0, 0),
        begin=datetime(2020, 1, 1, 0, 0, 0),
        end=datetime(2020, 1, 1, 1, 0, 0),
        amount=100,
        sector='DK1',
        technology_code='T020202',
        fuel_code='F02020202',
        issued=False,
        stored=False,
        retired=False,
        synchronized=False,
        locked=False,
    ))

    session.add(Ggo(
        id=3,
        user=user1,
        address='3',
        issue_time=datetime(2020, 1, 1, 0, 0, 0),
        expire_time=datetime(2030, 1, 1, 0, 0, 0),
        begin=datetime(2020, 1, 1, 0, 0, 0),
        end=datetime(2020, 1, 1, 1, 0, 0),
        amount=100,
        sector='DK1',
        technology_code='T010101',
        fuel_code='F02020202',
        issued=True,
        stored=False,
        retired=False,
        synchronized=False,
        locked=False,
    ))

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

        session1 = Session()
        seed_ggo_test_data(session1)
        session1.close()

        session2 = Session()
        yield session2
        session2.close()


# -- TEST CASES --------------------------------------------------------------


@pytest.mark.parametrize('ggo_id, technology', (
        (1, 'Solar'),
        (2, 'Wind'),
))
def test__Ggo__technology__Technology_exists__returns_correct_Technology(seeded_session, ggo_id, technology):
    query = GgoQuery(seeded_session).has_id(ggo_id)

    assert query.count() == 1
    assert query.one().technology.technology == technology


def test__Ggo__technology__Technology_does_not_exist__returns_None(seeded_session):
    query = GgoQuery(seeded_session).has_id(3)

    assert query.count() == 1
    assert query.one().technology is None


@patch('origin.ggo.models.KeyGenerator')
@pytest.mark.parametrize('ggo_id', (1, 2))
def test__Ggo__key__Ggo_was_NOT_issued__returns_get_key_for_traded_ggo(key_generator, ggo_id, seeded_session):
    ggo = GgoQuery(seeded_session).has_id(ggo_id).one()

    assert ggo.issued is False
    assert ggo.key is key_generator.get_key_for_traded_ggo.return_value
    key_generator.get_key_for_traded_ggo.assert_called_once_with(ggo)


@patch('origin.ggo.models.KeyGenerator')
def test__Ggo__key__Ggo_was_issued__returns_get_key_for_issued_ggo(key_generator, seeded_session):
    ggo = GgoQuery(seeded_session).has_id(3).one()

    assert ggo.issued is True
    assert ggo.key is key_generator.get_key_for_issued_ggo.return_value
    key_generator.get_key_for_issued_ggo.assert_called_once_with(ggo)


@pytest.mark.parametrize('amount', (-1, 0, 101))
def test__Ggo__create_child__amount_invalid__should_raise_AssertionError(amount, seeded_session):
    parent_ggo = GgoQuery(seeded_session).has_id(1).one()

    with pytest.raises(AssertionError):
        parent_ggo.create_child(amount, user2)


@pytest.mark.parametrize('ggo_id', (1, 2, 3))
def test__Ggo__create_child__returns_correctly_mapped_new_Ggo(ggo_id, seeded_session):
    parent_ggo = GgoQuery(seeded_session).has_id(ggo_id).one()
    child_ggo = parent_ggo.create_child(88, user2)

    assert child_ggo.parent_id == parent_ggo.id
    assert child_ggo.user_id == user2.id
    assert child_ggo.issue_time == parent_ggo.issue_time
    assert child_ggo.expire_time == parent_ggo.expire_time
    assert child_ggo.sector == parent_ggo.sector
    assert child_ggo.begin == parent_ggo.begin
    assert child_ggo.end == parent_ggo.end
    assert child_ggo.technology_code == parent_ggo.technology_code
    assert child_ggo.fuel_code == parent_ggo.fuel_code
    assert child_ggo.amount == 88
    assert child_ggo.issued is False
    assert child_ggo.stored is False
    assert child_ggo.retired is False
    assert child_ggo.synchronized is False
    assert child_ggo.locked is False
