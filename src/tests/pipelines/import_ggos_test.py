import time
import pytest
from itertools import cycle
from unittest.mock import patch, DEFAULT
from datetime import datetime, timedelta, timezone

from origin.ggo import Ggo
from origin.auth import User, MeteringPoint
from origin.pipelines.import_ggos import start_import_issued_ggos
from origin.services.datahub import (
    DataHubServiceConnectionError,
    DataHubServiceError,
)
from origin.webhooks import (
    WebhookConnectionError,
    WebhookError,
    WebhookSubscription,
    WebhookEvent,
)


gsrn1 = 'GSRN1'
begin1 = datetime(2020, 1, 1, 0, 0, tzinfo=timezone.utc)


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
    sub='38a7240c-088e-4659-bd66-d76afb8c762f',
    access_token='access_token',
    refresh_token='access_token',
    token_expire=datetime(2030, 1, 1, 0, 0, 0),
    master_extended_key=(
        'xprv9s21ZrQH143K2CK5syo8PdeX5Y4TYFkcU'
        'KonHhm1e7znhaKj6odQFbbBa7T2Y77AtiNmU6'
        'aatP2qJBTwvhqxvaSBHA9hEfZ5gViAS3bBj7F'
    ),
)

subscription1 = WebhookSubscription(
    id=1,
    event=WebhookEvent.ON_GGO_RECEIVED,
    subject=user1.sub,
    url='http://something.com',
    secret='something',
)

subscription2 = WebhookSubscription(
    id=2,
    event=WebhookEvent.ON_GGO_RECEIVED,
    subject=user1.sub,
    url='http://something-else.com',
    secret='something',
)

subscription3 = WebhookSubscription(
    id=3,
    event=WebhookEvent.ON_GGO_RECEIVED,
    subject=user2.sub,
    url='http://something.com',
    secret='something',
)


@pytest.fixture(scope='module')
def seeded_session(session):
    session.add(user1)
    session.add(user2)
    session.flush()

    session.add(subscription1)
    session.add(subscription2)
    session.add(subscription3)

    session.add(MeteringPoint.create(
        user=user1,
        session=session,
        gsrn=gsrn1,
        sector='DK1',
    ))
    session.flush()

    session.add(Ggo(
        user=user1,
        address='address',
        issue_time=datetime(2020, 1, 1, 0, 0, tzinfo=timezone.utc),
        expire_time=datetime(2030, 1, 1, 0, 0, tzinfo=timezone.utc),
        begin=begin1,
        end=begin1 + timedelta(hours=1),
        amount=100,
        sector='DK1',
        technology_code='T010101',
        fuel_code='F01010101',
        issued=True,
        stored=True,
        retired=False,
        synchronized=True,
        locked=False,
        issue_gsrn=gsrn1,
    ))

    session.flush()
    session.commit()

    yield session


# -- Test cases --------------------------------------------------------------


@patch('origin.db.make_session')
@patch('origin.pipelines.import_ggos.importer')
@patch('origin.pipelines.webhooks.webhook_service.on_ggo_received')
@patch('origin.pipelines.webhooks.invoke_on_ggo_received.default_retry_delay', 0)
@patch('origin.pipelines.import_ggos.import_ggos_and_insert_to_db.default_retry_delay', 0)
@patch('origin.pipelines.import_ggos.invoke_webhooks.default_retry_delay', 0)
@pytest.mark.usefixtures('celery_worker')
def test__import_ggos__happy_path__should_invoke_webhooks(
        on_ggo_received_mock, importer_mock, make_session_mock, seeded_session):

    make_session_mock.return_value = seeded_session

    # -- Arrange -------------------------------------------------------------

    def __import_ggos_and_assert(user, gsrn, begin_from, begin_to, session):
        # Assertion has to take place here, otherwise the User object is not bound
        # to a session anymore, hence the 'id' attribute is no longer available
        assert user.id == user1.id
        assert gsrn == gsrn1
        assert begin_from == begin1
        assert begin_to == begin1
        return session.query(Ggo).all()

    # importer_mock.import_ggos.return_value = __import_ggos_and_assert
    importer_mock.import_ggos.side_effect = __import_ggos_and_assert

    on_ggo_received_mock.side_effect = cycle((
        WebhookConnectionError(),
        WebhookError('', 0, ''),
        DEFAULT,
    ))

    # -- Act -----------------------------------------------------------------

    start_import_issued_ggos(user1.sub, gsrn1, begin1)

    # -- Assert --------------------------------------------------------------

    # # Wait for pipeline + linked tasks to finish
    time.sleep(10)

    # -- ledger.execute_batch()

    assert importer_mock.import_ggos.call_count == 1

    # -- webhook_service.on_measurement_published()

    assert on_ggo_received_mock.call_count == 2 * 3
