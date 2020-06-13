import pytest
import testing.postgresql
from celery.exceptions import Retry
from datetime import datetime
from sqlalchemy import create_engine, orm
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock, Mock, patch

from origin.auth import User
from origin.db import ModelBase
from origin.ledger import Batch, BatchState
from origin.pipelines.submit_batch_to_ledger import (
    submit_batch_to_ledger,
)


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

# meteringpoint1 = MeteringPoint(
#     id=1,
#     user=user1,
#     gsrn='GSRN1',
#     sector='DK1',
#     key_index=0,
# )
#
# meteringpoint2 = MeteringPoint(
#     id=2,
#     user=user2,
#     gsrn='GSRN2',
#     sector='DK1',
#     key_index=0,
# )


def seed_test_data(session):

    # Dependencies
    session.add(user1)
    session.add(user2)
    # session.add(meteringpoint1)
    # session.add(meteringpoint2)

    # Input for combinations

    session.add(Batch(
        id=1,
        state=BatchState.PENDING,
        user=user1,
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
        seed_test_data(session1)
        session1.close()

        session2 = Session()
        yield session2
        session2.close()


# -- TEST CASES --------------------------------------------------------------


@patch('origin.db.make_session')
def test__submit_batch_to_ledger__submit_batch_to_ledger__batch_does_not_exist__should_raise_NoResultFound(make_session_mock, seeded_session):

    make_session_mock.return_value = seeded_session

    with pytest.raises(orm.exc.NoResultFound):
        submit_batch_to_ledger(subject='subject', batch_id=0)


@patch('origin.db.make_session')
def test__submit_batch_to_ledger__submit_batch_to_ledger__load_batch_resulted_in_unexpected_exception__should_raise_Retry(make_session_mock, seeded_session):

    class ArbitraryException(Exception):
        pass

    def __mock_query(*args, **kwargs):
        raise Exception

    seeded_session.query = __mock_query

    make_session_mock.return_value = seeded_session

    with pytest.raises(Retry):
        submit_batch_to_ledger(subject='subject', batch_id=1)
