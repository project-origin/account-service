import pytest
import testing.postgresql
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from origin.db import ModelBase
from origin.auth import User
from origin.ggo.models import GgoIndexSequence


GGO_AMOUNT = 75


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


def seed_user_data(session):
    session.add(user1)
    session.add(user2)
    session.flush()
    session.commit()


@pytest.fixture(scope='module')
def seeded_session():
    with testing.postgresql.Postgresql() as psql:
        engine = create_engine(psql.url())
        ModelBase.metadata.create_all(engine)
        Session = sessionmaker(bind=engine, expire_on_commit=False)

        session1 = Session()
        seed_user_data(session1)
        session1.close()

        session2 = Session()
        yield session2
        session2.close()


# -- TEST CASES --------------------------------------------------------------


def test__GgoIndexSequence__get_next(seeded_session):
    assert GgoIndexSequence.get_next(user1.id, seeded_session) == 0
    assert GgoIndexSequence.get_next(user1.id, seeded_session) == 1
    assert GgoIndexSequence.get_next(user1.id, seeded_session) == 2

    assert GgoIndexSequence.get_next(user2.id, seeded_session) == 0
    assert GgoIndexSequence.get_next(user2.id, seeded_session) == 1
    assert GgoIndexSequence.get_next(user2.id, seeded_session) == 2

    assert GgoIndexSequence.get_next(user1.id, seeded_session) == 3
    assert GgoIndexSequence.get_next(user1.id, seeded_session) == 4
    assert GgoIndexSequence.get_next(user1.id, seeded_session) == 5

    assert GgoIndexSequence.get_next(user2.id, seeded_session) == 3
    assert GgoIndexSequence.get_next(user2.id, seeded_session) == 4
    assert GgoIndexSequence.get_next(user2.id, seeded_session) == 5

    with pytest.raises(IntegrityError):
        GgoIndexSequence.get_next(123456789, seeded_session)
