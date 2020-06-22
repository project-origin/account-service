import os
import time
import pytest
import origin_ledger_sdk as ols

from uuid import uuid4
from unittest.mock import patch
from datetime import datetime, timezone
from celery.backends.redis import RedisBackend
from origin_ledger_sdk.ledger_connector import BatchStatusResponse

from origin.auth import User, MeteringPoint
from origin.ledger import Batch, BatchState
from origin.pipelines import start_handle_composed_ggo_pipeline
from origin.ggo import Ggo, GgoComposer
from origin.pipelines.submit_batch_to_ledger import InvalidBatch
from origin.tasks import celery_app
from origin.webhooks import WebhookSubscription, WebhookEvent


PIPELINE_TIMEOUT = 60 * 5  # Seconds
CURRENT_FOLDER = os.path.split(os.path.abspath(__file__))[0]


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
        'xprv9s21ZrQH143K4WQcTeFMi8gfrgHYuoFH2'
        '63xo4YPAqMN6RGc2BJeAghBtcxf1BzQz81ynY'
        'fZpchrt3tGRBpQn1jp1bNH41AisDWfKQi57MM'
    ),
)

user3 = User(
    id=3,
    sub='e7132e48-8969-4cba-9130-55fddf28df91',
    access_token='access_token',
    refresh_token='access_token',
    token_expire=datetime(2030, 1, 1, 0, 0, 0),
    master_extended_key=(
        'xprv9s21ZrQH143K2SJ98GWKgbEemXLA6SShS'
        'iNTuCAPAeM9RfdYqpqxLxp4ogPSvYfv6tfdSJ'
        'dQo1WTPMatwovVBuWgyBi1RewZC7JUFY9y5Ww'
    ),
)


subscription1 = WebhookSubscription(
    id=1,
    event=WebhookEvent.ON_GGO_RECEIVED,
    subject=user2.sub,
    url='http://something.com',
    secret='something',
)

subscription2 = WebhookSubscription(
    id=2,
    event=WebhookEvent.ON_GGO_RECEIVED,
    subject=user2.sub,
    url='http://something-else.com',
    secret='something',
)

subscription3 = WebhookSubscription(
    id=3,
    event=WebhookEvent.ON_GGO_RECEIVED,
    subject=user3.sub,
    url='http://something.com',
    secret='something',
)

subscription4 = WebhookSubscription(
    id=4,
    event=WebhookEvent.ON_GGO_RECEIVED,
    subject=user3.sub,
    url='http://something-else.com',
    secret='something',
)


def create_batch(session):
    ggo = Ggo(
        user=user1,
        address=str(uuid4()),
        issue_time=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        expire_time=datetime(2050, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        begin=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        end=datetime(2020, 1, 1, 1, 0, 0, tzinfo=timezone.utc),
        amount=100,
        sector='DK1',
        technology_code='T000000',
        fuel_code='F00000000',
        issued=True,
        stored=True,
        retired=False,
        synchronized=True,
        locked=False,
        issue_gsrn='GSRN1',
    )

    session.add(ggo)

    composer = GgoComposer(ggo=ggo, session=session)
    composer.add_transfer(user2, 25)
    composer.add_transfer(user3, 75)
    batch, recipients = composer.build_batch()
    session.add(batch)
    session.flush()
    session.commit()

    return batch, recipients


@pytest.fixture(scope='module')
def seeded_session(session):
    """
    Returns a Session object with Ggo + User data seeded for testing
    """
    session.add(user1)
    session.add(user2)
    session.add(user3)
    session.add(subscription1)
    session.add(subscription2)
    session.add(subscription3)
    session.add(subscription4)
    session.flush()

    session.add(MeteringPoint.create(
        user=user1,
        session=session,
        gsrn='GSRN1',
        sector='DK1',
    ))

    session.flush()
    session.commit()

    yield session


@pytest.fixture(scope='module')
def celery_config(redis):
    redis_host, redis_port = redis
    redis_url = f'redis://:@{redis_host}:{redis_port}'

    REDIS_BROKER_URL = f'{redis_url}/0'

    celery_app.backend = RedisBackend(app=celery_app, url=f'{redis_url}/1')
    celery_app.conf.broker_url = REDIS_BROKER_URL
    celery_app.conf.broker_read_url = REDIS_BROKER_URL
    celery_app.conf.broker_write_url = REDIS_BROKER_URL

    return {
        'broker_url': f'{redis_url}/0',
        'result_backend': f'{redis_url}/1',
    }


# -- Constructor -------------------------------------------------------------


@patch('origin.db.make_session')
@patch('origin.ledger.models.Batch.build_ledger_batch')
@patch('origin.pipelines.submit_batch_to_ledger.ledger')
@patch('origin.pipelines.webhooks.webhook_service.on_ggo_received')
@pytest.mark.usefixtures('celery_worker')
def test__handle_composed_ggo__happy_path__Batch_should_be_COMPLETED(
        on_ggo_received_mock, ledger_mock, build_ledger_batch, make_session_mock, seeded_session):

    # -- Arrange -------------------------------------------------------------

    make_session_mock.return_value = seeded_session
    build_ledger_batch.return_value = 'LEDGER BATCH'

    # Executing batch: Raises Ledger exceptions a few times, then returns Handle
    ledger_mock.execute_batch.side_effect = (
        ols.LedgerConnectionError(),
        ols.LedgerException('', code=15),
        ols.LedgerException('', code=17),
        ols.LedgerException('', code=18),
        ols.LedgerException('', code=31),
        'LEDGER-HANDLE',
    )

    # Getting batch status: Raises LedgerConnectionError once, then returns BatchStatuses
    ledger_mock.get_batch_status.side_effect = (
        ols.LedgerConnectionError(),
        BatchStatusResponse(id='', status=ols.BatchStatus.UNKNOWN),
        BatchStatusResponse(id='', status=ols.BatchStatus.PENDING),
        BatchStatusResponse(id='', status=ols.BatchStatus.COMMITTED),
    )

    # -- Act -----------------------------------------------------------------

    batch, recipients = create_batch(seeded_session)
    pipeline = start_handle_composed_ggo_pipeline(batch, recipients, seeded_session)

    # -- Assert --------------------------------------------------------------

    # Wait for pipeline + linked tasks to finish
    pipeline.get(timeout=PIPELINE_TIMEOUT)
    [c.get(timeout=PIPELINE_TIMEOUT) for c in pipeline.children]

    # ledger.execute_batch()
    assert ledger_mock.execute_batch.call_count == 6
    assert all(args == (('LEDGER BATCH',),) for args in ledger_mock.execute_batch.call_args_list)

    # ledger.get_batch_status()
    assert ledger_mock.get_batch_status.call_count == 4
    assert all(args == (('LEDGER-HANDLE',),) for args in ledger_mock.get_batch_status.call_args_list)

    # webhook_service.on_ggo_received_mock()
    assert on_ggo_received_mock.call_count == 4

    for split_target in batch.transactions[0].targets:
        if split_target.ggo.user_id == user2.id:
            assert any(
                isinstance(args[0][0], WebhookSubscription) and
                args[0][0].id == subscription1.id and
                isinstance(args[0][1], Ggo) and
                args[0][1].id == split_target.ggo.id
                for args in on_ggo_received_mock.call_args_list
            )
            assert any(
                isinstance(args[0][0], WebhookSubscription) and
                args[0][0].id == subscription2.id and
                isinstance(args[0][1], Ggo) and
                args[0][1].id == split_target.ggo.id
                for args in on_ggo_received_mock.call_args_list
            )
        elif split_target.ggo.user_id == user3.id:
            assert any(
                isinstance(args[0][0], WebhookSubscription) and
                args[0][0].id == subscription3.id and
                isinstance(args[0][1], Ggo) and
                args[0][1].id == split_target.ggo.id
                for args in on_ggo_received_mock.call_args_list
            )
            assert any(
                isinstance(args[0][0], WebhookSubscription) and
                args[0][0].id == subscription4.id and
                isinstance(args[0][1], Ggo) and
                args[0][1].id == split_target.ggo.id
                for args in on_ggo_received_mock.call_args_list
            )
        else:
            raise RuntimeError

    # Batch state after pipeline completes
    batch = seeded_session.query(Batch).filter_by(id=batch.id).one()
    assert batch.state is BatchState.COMPLETED


@patch('origin.db.make_session')
@patch('origin.ledger.models.Batch.build_ledger_batch')
@patch('origin.pipelines.submit_batch_to_ledger.ledger')
@patch('origin.pipelines.webhooks.webhook_service.on_ggo_received')
@pytest.mark.usefixtures('celery_worker')
def test__handle_composed_ggo__execute_batch_raises_LedgerException__Batch_should_be_DECLINED(
        on_ggo_received_mock, ledger_mock, build_ledger_batch, make_session_mock, seeded_session):

    # -- Arrange -------------------------------------------------------------

    make_session_mock.return_value = seeded_session
    build_ledger_batch.return_value = 'LEDGER BATCH'

    # Executing batch: Raises Ledger exceptions a few times, then returns Handle
    ledger_mock.execute_batch.side_effect = (
        ols.LedgerException('', code=10),
    )

    # -- Act -----------------------------------------------------------------

    batch, recipients = create_batch(seeded_session)
    pipeline = start_handle_composed_ggo_pipeline(batch, recipients, seeded_session)

    # -- Assert --------------------------------------------------------------

    # Wait for pipeline + linked tasks to finish
    with pytest.raises(ols.LedgerException):
        pipeline.get(timeout=PIPELINE_TIMEOUT)

    time.sleep(5)

    # ledger.execute_batch()
    ledger_mock.execute_batch.assert_called_once_with('LEDGER BATCH')
    ledger_mock.get_batch_status.assert_not_called()
    on_ggo_received_mock.assert_not_called()

    # Batch state after pipeline completes
    batch = seeded_session.query(Batch).filter_by(id=batch.id).one()
    assert batch.state is BatchState.DECLINED


@patch('origin.db.make_session')
@patch('origin.ledger.models.Batch.build_ledger_batch')
@patch('origin.pipelines.submit_batch_to_ledger.ledger')
@patch('origin.pipelines.webhooks.webhook_service.on_ggo_received')
@pytest.mark.usefixtures('celery_worker')
def test__handle_composed_ggo__get_batch_status_raises_LedgerException__Batch_should_be_DECLINED(
        on_ggo_received_mock, ledger_mock, build_ledger_batch, make_session_mock, seeded_session):

    # -- Arrange -------------------------------------------------------------

    make_session_mock.return_value = seeded_session
    build_ledger_batch.return_value = 'LEDGER BATCH'

    # Executing batch: Returns Handle
    ledger_mock.execute_batch.side_effect = (
        'LEDGER-HANDLE',
    )

    # Getting batch status: Raises LedgerException
    ledger_mock.get_batch_status.side_effect = (
        ols.LedgerException('', code=10),
    )

    # -- Act -----------------------------------------------------------------

    batch, recipients = create_batch(seeded_session)
    pipeline = start_handle_composed_ggo_pipeline(batch, recipients, seeded_session)

    # -- Assert --------------------------------------------------------------

    # Wait for pipeline + linked tasks to finish
    with pytest.raises(ols.LedgerException):
        pipeline.get(timeout=PIPELINE_TIMEOUT)

    time.sleep(5)

    # ledger.execute_batch()
    ledger_mock.execute_batch.assert_called_once_with('LEDGER BATCH')
    ledger_mock.get_batch_status.assert_called_once_with('LEDGER-HANDLE')
    on_ggo_received_mock.assert_not_called()

    # Batch state after pipeline completes
    batch = seeded_session.query(Batch).filter_by(id=batch.id).one()
    assert batch.state is BatchState.DECLINED


@patch('origin.db.make_session')
@patch('origin.ledger.models.Batch.build_ledger_batch')
@patch('origin.pipelines.submit_batch_to_ledger.ledger')
@patch('origin.pipelines.webhooks.webhook_service.on_ggo_received')
@pytest.mark.usefixtures('celery_worker')
def test__handle_composed_ggo__get_batch_status_returns_INVALID__Batch_should_be_DECLINED(
        on_ggo_received_mock, ledger_mock, build_ledger_batch, make_session_mock, seeded_session):

    # -- Arrange -------------------------------------------------------------

    make_session_mock.return_value = seeded_session
    build_ledger_batch.return_value = 'LEDGER BATCH'

    # Executing batch: Returns Handle
    ledger_mock.execute_batch.side_effect = (
        'LEDGER-HANDLE',
    )

    # Getting batch status: Raises LedgerException
    ledger_mock.get_batch_status.side_effect = (
        BatchStatusResponse(id='', status=ols.BatchStatus.INVALID),
    )

    # -- Act -----------------------------------------------------------------

    batch, recipients = create_batch(seeded_session)
    pipeline = start_handle_composed_ggo_pipeline(batch, recipients, seeded_session)

    # -- Assert --------------------------------------------------------------

    # Wait for pipeline + linked tasks to finish
    with pytest.raises(InvalidBatch):
        pipeline.get(timeout=PIPELINE_TIMEOUT)

    time.sleep(5)

    # ledger.execute_batch()
    ledger_mock.execute_batch.assert_called_once_with('LEDGER BATCH')
    ledger_mock.get_batch_status.assert_called_once_with('LEDGER-HANDLE')
    on_ggo_received_mock.assert_not_called()

    # Batch state after pipeline completes
    batch = seeded_session.query(Batch).filter_by(id=batch.id).one()
    assert batch.state is BatchState.DECLINED
