import pytest
import testing.postgresql
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
from itertools import product

from origin.db import ModelBase
from origin.auth import User
from origin.ggo.models import Ggo
from origin.ggo.queries import TransactionQuery
from origin.ledger import Batch, BatchState, SplitTransaction


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

user3 = User(
    id=3,
    sub='7169e62d-e349-4af2-9587-6027a4e86cf9',
    access_token='access_token',
    refresh_token='access_token',
    token_expire=datetime(2030, 1, 1, 0, 0, 0),
    master_extended_key=(
        'xprv9s21ZrQH143K2CK5syo8PdeX5Y4TYFkcU'
        'KonHhm1e7znhaKj6odQFbbBa7T2Y77AtiNmU6'
        'aatP2qJBTwvhqxvaSBHA9hEfZ5gViAS3bBj7F'
    ),
)

user4 = User(
    id=4,
    sub='7eca644f-b6df-42e5-b6ae-03cb490678c9',
    access_token='access_token',
    refresh_token='access_token',
    token_expire=datetime(2030, 1, 1, 0, 0, 0),
    master_extended_key=(
        'xprv9s21ZrQH143K2CK5syo8PdeX5Y4TYFkcU'
        'KonHhm1e7znhaKj6odQFbbBa7T2Y77AtiNmU6'
        'aatP2qJBTwvhqxvaSBHA9hEfZ5gViAS3bBj7F'
    ),
)

user5 = User(
    id=5,
    sub='08556bee-76d9-4f94-916b-ee577ee01c60',
    access_token='access_token',
    refresh_token='access_token',
    token_expire=datetime(2030, 1, 1, 0, 0, 0),
    master_extended_key=(
        'xprv9s21ZrQH143K2CK5syo8PdeX5Y4TYFkcU'
        'KonHhm1e7znhaKj6odQFbbBa7T2Y77AtiNmU6'
        'aatP2qJBTwvhqxvaSBHA9hEfZ5gViAS3bBj7F'
    ),
)


def seed_transaction_test_data(session):

    # Dependencies
    session.add(user1)
    session.add(user2)
    session.add(user3)
    session.add(user4)
    session.add(user5)

    # Input for combinations
    users = (user1, user2, user3, user4)
    references = (None, 'REF1', 'REF2', 'REF3')

    # Seed transactions (+ GGOs)
    for i, (usr, ref) in enumerate(product(users, references), start=1):
        ggo = Ggo(
            user=usr,
            address=str(i**5),
            issue_time=datetime(2020, 1, 1, 0, 0, 0),
            expire_time=datetime(2030, 1, 1, 0, 0, 0),
            begin=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            end=datetime(2020, 1, 1, 1, 0, 0, tzinfo=timezone.utc),
            amount=GGO_AMOUNT,
            sector='DK1',
            technology_code='T010000',
            fuel_code='F00000000',
            issued=False,
            stored=False,
            retired=False,
            synchronized=False,
            locked=False,
        )

        transaction = SplitTransaction(parent_ggo=ggo)
        other_users = [u for u in users if u is not usr]

        for j, target_user in enumerate(other_users, start=1):
            transaction.add_target(
                reference=ref,
                ggo=Ggo(
                    parent=ggo,
                    user=target_user,
                    address=str(i**5 + j),
                    issue_time=datetime(2020, 1, 1, 0, 0, 0),
                    expire_time=datetime(2030, 1, 1, 0, 0, 0),
                    begin=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                    end=datetime(2020, 1, 1, 1, 0, 0, tzinfo=timezone.utc),
                    amount=int(GGO_AMOUNT / 3),
                    sector='DK1',
                    technology_code='T010000',
                    fuel_code='F00000000',
                    issued=False,
                    stored=False,
                    retired=False,
                    synchronized=False,
                    locked=False,
                ),
            )

        batch = Batch(
            user=usr,
            state=BatchState.COMPLETED,
        )
        batch.add_transaction(transaction)

        session.add(batch)

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

        seed_transaction_test_data(session)

        yield session

        session.close()


# -- TEST CASES --------------------------------------------------------------


@pytest.mark.parametrize('user', (user1, user2, user3, user4))
def test__TransactionQuery__sent_by_user__Ggos_exists__returns_correct_Ggos(seeded_session, user):
    query = TransactionQuery(seeded_session) \
        .sent_by_user(user)

    assert query.count() > 0
    assert all(ggo.parent.user_id == user.id for ggo in query.all())


def test__TransactionQuery__sent_by_user__Ggos_does_not_exists__returns_nothing(seeded_session):
    query = TransactionQuery(seeded_session) \
        .sent_by_user(user5)

    assert query.count() == 0


@pytest.mark.parametrize('user', (user1, user2, user3, user4))
def test__TransactionQuery__received_by_user__Ggos_exists__returns_correct_Ggos(seeded_session, user):
    query = TransactionQuery(seeded_session) \
        .received_by_user(user)

    assert query.count() > 0
    assert all(ggo.user_id == user.id for ggo in query.all())


def test__TransactionQuery__received_by_user__Ggos_does_not_exists__returns_nothing(seeded_session):
    query = TransactionQuery(seeded_session) \
        .received_by_user(user5)

    assert query.count() == 0


@pytest.mark.parametrize('user', (user1, user2, user3, user4))
def test__TransactionQuery__sent_or_received_by_user__Ggos_exists__returns_correct_Ggos(seeded_session, user):
    query = TransactionQuery(seeded_session) \
        .sent_or_received_by_user(user)

    assert query.count() > 0
    assert all(ggo.user_id == user.id or ggo.parent.user_id == user.id
               for ggo in query.all())


@pytest.mark.parametrize('user', (user1, user2, user3, user4))
def test__TransactionQuery__sent_or_received_by_user__Ggos_does_not_exists__returns_nothing(seeded_session, user):
    query = TransactionQuery(seeded_session) \
        .sent_or_received_by_user(user5)

    assert query.count() == 0


@pytest.mark.parametrize('reference', (None, 'REF1', 'REF2', 'REF3'))
def test__TransactionQuery__has_reference__Ggos_exists__returns_correct_Ggos(seeded_session, reference):
    query = TransactionQuery(seeded_session) \
        .has_reference(reference)

    assert query.count() == 12


def test__TransactionQuery__has_reference__Ggos_does_not_exists__returns_nothing(seeded_session):
    query = TransactionQuery(seeded_session) \
        .has_reference('A-REFERENCE-THAT-DOESNT-EXISTS')

    assert query.count() == 0
