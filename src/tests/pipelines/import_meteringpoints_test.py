import time
import pytest
from itertools import cycle
from datetime import datetime
from unittest.mock import patch

from origin.auth import User, MeteringPointQuery
from origin.pipelines import start_import_meteringpoints_for
from origin.services.datahub import (
    DataHubServiceError,
    DataHubServiceConnectionError,
    GetMeteringPointsResponse,
    SetKeyResponse,
    MeteringPoint as DataHubMeteringPoint,
    MeteringPointType as DataHubMeteringPointType,
)


gsrn1 = 'GSRN1'
gsrn2 = 'GSRN2'


meteringpoint1 = DataHubMeteringPoint(
    gsrn=gsrn1,
    type=DataHubMeteringPointType.PRODUCTION,
    sector='DK1',
)

meteringpoint2 = DataHubMeteringPoint(
    gsrn=gsrn2,
    type=DataHubMeteringPointType.PRODUCTION,
    sector='DK2'
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


@pytest.fixture(scope='module')
def seeded_session(session):
    session.add(user1)
    session.flush()
    session.commit()
    yield session


# -- Test cases --------------------------------------------------------------


@patch('origin.db.make_session')
@patch('origin.pipelines.import_meteringpoints.datahub_service')
@patch('origin.pipelines.import_meteringpoints.import_meteringpoints_and_insert_to_db.default_retry_delay', 0)
@patch('origin.pipelines.import_meteringpoints.send_key_to_datahub_service.default_retry_delay', 0)
@pytest.mark.usefixtures('celery_worker')
def test__import_meteringpoints__happy_path__should_send_MeteringPoint_key_to_DataHubService_for_each_new_MeteringPoint_imported(
        datahub_service_mock, make_session_mock, seeded_session):

    # -- Arrange -------------------------------------------------------------

    make_session_mock.return_value = seeded_session

    datahub_service_mock.get_meteringpoints.side_effect = cycle((
        DataHubServiceConnectionError(),
        DataHubServiceError('', 0, ''),
        GetMeteringPointsResponse(
            success=True,
            meteringpoints=[meteringpoint1, meteringpoint2]
        ),
    ))

    datahub_service_mock.set_key.side_effect = cycle((
        DataHubServiceConnectionError(),
        DataHubServiceError('', 0, ''),
        SetKeyResponse(success=True),
    ))

    # -- Act -----------------------------------------------------------------

    start_import_meteringpoints_for(user1.sub)
    start_import_meteringpoints_for(user1.sub)

    # -- Assert --------------------------------------------------------------

    time.sleep(10)

    # Database state
    assert MeteringPointQuery(seeded_session).count() == 2
    assert MeteringPointQuery(seeded_session).has_gsrn(gsrn1).count() == 1
    assert MeteringPointQuery(seeded_session).has_gsrn(gsrn1).one().sector == 'DK1'
    assert MeteringPointQuery(seeded_session).has_gsrn(gsrn2).count() == 1
    assert MeteringPointQuery(seeded_session).has_gsrn(gsrn2).one().sector == 'DK2'

    # datahub_service.get_meteringpoints()
    assert datahub_service_mock.get_meteringpoints.call_count == 2 * 3
    assert all(args == ((user1.access_token,),) for args in datahub_service_mock.get_meteringpoints.call_args_list)

    # datahub_service.set_key()
    assert datahub_service_mock.set_key.call_count == 2 * 3

    datahub_service_mock.set_key.assert_any_call(
        token=user1.access_token,
        gsrn=meteringpoint1.gsrn,
        key=MeteringPointQuery(seeded_session).has_gsrn(meteringpoint1.gsrn).one().extended_key,
    )

    datahub_service_mock.set_key.assert_any_call(
        token=user1.access_token,
        gsrn=meteringpoint2.gsrn,
        key=MeteringPointQuery(seeded_session).has_gsrn(meteringpoint2.gsrn).one().extended_key,
    )
