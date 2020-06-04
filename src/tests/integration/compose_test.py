import pytest
import testing.postgresql
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from origin.db import ModelBase
from origin.auth import User, MeteringPoint
from origin.services.datahub import (
    Measurement,
    MeasurementType,
    GetMeasurementResponse,
    GetGgoListResponse,
    Ggo as GgoDataHub,
)
from origin.ggo import (
    Ggo,
    GgoIndexSequence,
    GgoComposer,
    GgoIssueController,
    GgoQuery,
    RetireQuery,
    TransactionQuery,
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

user4 = User(
    id=4,
    sub='2e93d6fb-6c91-480b-827a-24d965ac7b00',
    access_token='access_token',
    refresh_token='access_token',
    token_expire=datetime(2030, 1, 1, 0, 0, 0),
    master_extended_key=(
        'xprv9s21ZrQH143K3twCsVmArteJpkTDmFyz8'
        'p74RhZW27GpTQcAsKUsdTfE17oRLKdHWfRKwm'
        'sPERLVFBL7ucPYthR7TNuN11yQyfPgkU3wfC6'
    ),
)


def seed_users(session):
    session.add(user1)
    session.add(user2)
    session.add(user3)
    session.add(user4)
    session.flush()
    session.commit()


@pytest.fixture(scope='module')
def session():
    """
    Returns a Session object with Ggo + User data seeded for testing
    """
    with testing.postgresql.Postgresql() as psql:
        engine = create_engine(psql.url())
        ModelBase.metadata.create_all(engine)
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        session = Session()

        seed_users(session)

        yield session

        session.close()


# -- Constructor -------------------------------------------------------------


@patch('origin.ggo.composer.datahub')
@patch('origin.ggo.issuing.datahub')
def test__integration__compose(datahub_issuing, datahub_composer, session):

    sector = 'DK1'
    begin = datetime(2020, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
    end = begin + timedelta(hours=1)
    ref1 = 'REF1'
    ref2 = 'REF2'
    gsrn1 = '1111111111'
    gsrn2 = '2222222222'

    issued_ggo1 = GgoDataHub(
        address='address1',
        gsrn=gsrn1,
        begin=begin,
        end=end,
        sector=sector,
        amount=100,
        issue_time=str(datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)),
        expire_time=str(datetime(2050, 1, 1, 0, 0, 0, tzinfo=timezone.utc)),
        technology_code='T000000',
        fuel_code='F00000000',
    )

    issued_ggo2 = GgoDataHub(
        address='address2',
        gsrn=gsrn1,
        begin=begin,
        end=end,
        sector=sector,
        amount=100,
        issue_time=str(datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)),
        expire_time=str(datetime(2050, 1, 1, 0, 0, 0, tzinfo=timezone.utc)),
        technology_code='T000000',
        fuel_code='F00000000',
    )

    measurement1 = Measurement(
        address='measurement1',
        gsrn=gsrn1,
        begin=begin,
        end=end,
        type=MeasurementType.CONSUMPTION,
        sector=sector,
        amount=10,
    )

    measurement2 = Measurement(
        address='measurement2',
        gsrn=gsrn2,
        begin=begin,
        end=end,
        type=MeasurementType.CONSUMPTION,
        sector=sector,
        amount=10,
    )

    meteringpoint1 = MeteringPoint.create(
        user=user1,
        session=session,
        gsrn=gsrn1,
        sector=sector,
    )

    meteringpoint2 = MeteringPoint.create(
        user=user1,
        session=session,
        gsrn=gsrn2,
        sector=sector,
    )

    session.add(meteringpoint1)
    session.add(meteringpoint2)
    session.flush()
    session.commit()

    # -- ARRANGE DATAHUB MOCK (for issuer) -----------------------------------

    datahub_issuing.get_ggo_list.side_effect = \
        lambda *args, **kwargs: GetGgoListResponse(success=True, ggos=[issued_ggo1, issued_ggo2])

    # -- ARRANGE DATAHUB MOCK (for composer) ---------------------------------

    def __get_consumption(access_token, request):
        if (request.gsrn, request.begin) == (meteringpoint1.gsrn, begin):
            m = measurement1
        elif (request.gsrn, request.begin) == (meteringpoint2.gsrn, begin):
            m = measurement2
        else:
            raise RuntimeError

        return GetMeasurementResponse(success=True, measurement=m)

    datahub_composer.get_consumption.side_effect = __get_consumption

    # -- ISSUE GGOS ----------------------------------------------------------

    issuer = GgoIssueController()
    issuer.import_ggos(user1, meteringpoint1.gsrn, begin, begin, session)

    session.commit()

    parent_ggo1 = GgoQuery(session).has_address('address1').one()
    parent_ggo2 = GgoQuery(session).has_address('address2').one()

    # -- ASSERT --------------------------------------------------------------

    assert GgoQuery(session).belongs_to(user1).is_stored().get_total_amount() == 200
    assert GgoQuery(session).belongs_to(user2).is_stored().get_total_amount() == 0
    assert GgoQuery(session).belongs_to(user3).is_stored().get_total_amount() == 0
    assert TransactionQuery(session).sent_by_user(user1).get_total_amount() == 0
    assert TransactionQuery(session).sent_by_user(user2).get_total_amount() == 0
    assert TransactionQuery(session).sent_by_user(user3).get_total_amount() == 0
    assert TransactionQuery(session).received_by_user(user1).get_total_amount() == 0
    assert TransactionQuery(session).received_by_user(user2).get_total_amount() == 0
    assert TransactionQuery(session).received_by_user(user3).get_total_amount() == 0
    assert RetireQuery(session).belongs_to(user1).get_total_amount() == 0
    assert RetireQuery(session).belongs_to(user2).get_total_amount() == 0
    assert RetireQuery(session).belongs_to(user3).get_total_amount() == 0
    assert RetireQuery(session).is_retired_to_gsrn(meteringpoint1.gsrn).get_total_amount() == 0
    assert RetireQuery(session).is_retired_to_gsrn(meteringpoint2.gsrn).get_total_amount() == 0

    # -- ACT -----------------------------------------------------------------

    # TRANSFER 40, RETIRE 15 (5 + 10) = TOTAL 60, REMAINING 40
    composer = GgoComposer(ggo=parent_ggo1, session=session)
    composer.add_transfer(user2, 10, ref1)
    composer.add_transfer(user3, 30, ref2)
    composer.add_retire(meteringpoint1, 5)   # Measurement = 10
    composer.add_retire(meteringpoint2, 15)  # Measurement = 10, so actually only 10 (5 is ignored)

    batch1, recipients = composer.build_batch()

    session.add(batch1)
    session.commit()

    # -- ASSERT --------------------------------------------------------------

    assert GgoQuery(session).belongs_to(user1).is_stored().get_total_amount() == 100
    assert GgoQuery(session).belongs_to(user2).is_stored().get_total_amount() == 0
    assert GgoQuery(session).belongs_to(user3).is_stored().get_total_amount() == 0
    assert TransactionQuery(session).sent_by_user(user1).get_total_amount() == 40
    assert TransactionQuery(session).sent_by_user(user2).get_total_amount() == 0
    assert TransactionQuery(session).sent_by_user(user3).get_total_amount() == 0
    assert TransactionQuery(session).received_by_user(user1).get_total_amount() == 0
    assert TransactionQuery(session).received_by_user(user2).get_total_amount() == 10
    assert TransactionQuery(session).received_by_user(user3).get_total_amount() == 30
    assert RetireQuery(session).belongs_to(user1).get_total_amount() == 15
    assert RetireQuery(session).belongs_to(user2).get_total_amount() == 0
    assert RetireQuery(session).belongs_to(user3).get_total_amount() == 0
    assert RetireQuery(session).is_retired_to_gsrn(meteringpoint1.gsrn).get_total_amount() == 5
    assert RetireQuery(session).is_retired_to_gsrn(meteringpoint2.gsrn).get_total_amount() == 10

    # -- ACT -----------------------------------------------------------------

    batch1.on_commit()
    session.commit()

    # -- ASSERT --------------------------------------------------------------

    assert GgoQuery(session).belongs_to(user1).is_stored().get_total_amount() == 145
    assert GgoQuery(session).belongs_to(user2).is_stored().get_total_amount() == 10
    assert GgoQuery(session).belongs_to(user3).is_stored().get_total_amount() == 30
    assert TransactionQuery(session).sent_by_user(user1).get_total_amount() == 40
    assert TransactionQuery(session).sent_by_user(user2).get_total_amount() == 0
    assert TransactionQuery(session).sent_by_user(user3).get_total_amount() == 0
    assert TransactionQuery(session).received_by_user(user1).get_total_amount() == 0
    assert TransactionQuery(session).received_by_user(user2).get_total_amount() == 10
    assert TransactionQuery(session).received_by_user(user3).get_total_amount() == 30
    assert RetireQuery(session).belongs_to(user1).get_total_amount() == 15
    assert RetireQuery(session).belongs_to(user2).get_total_amount() == 0
    assert RetireQuery(session).belongs_to(user3).get_total_amount() == 0
    assert RetireQuery(session).is_retired_to_gsrn(meteringpoint1.gsrn).get_total_amount() == 5
    assert RetireQuery(session).is_retired_to_gsrn(meteringpoint2.gsrn).get_total_amount() == 10

    # -- ACT -----------------------------------------------------------------

    # TRANSFER 40, RETIRE 5 (5 + 0) = TOTAL 45, REMAINING 55
    composer = GgoComposer(ggo=parent_ggo2, session=session)
    composer.add_transfer(user2, 10, ref1)
    composer.add_transfer(user3, 30, ref2)
    composer.add_retire(meteringpoint1, 5)   # Measurement = 10, so actually only 5 (5 already retired)
    composer.add_retire(meteringpoint2, 15)  # Measurement = 10, so actually 0 (10 already retired)

    batch2, recipients = composer.build_batch()

    session.add(batch2)
    session.commit()

    # -- ASSERT --------------------------------------------------------------

    assert GgoQuery(session).belongs_to(user1).is_stored().get_total_amount() == 45
    assert GgoQuery(session).belongs_to(user2).is_stored().get_total_amount() == 10
    assert GgoQuery(session).belongs_to(user3).is_stored().get_total_amount() == 30
    assert TransactionQuery(session).sent_by_user(user1).get_total_amount() == 80
    assert TransactionQuery(session).sent_by_user(user2).get_total_amount() == 0
    assert TransactionQuery(session).sent_by_user(user3).get_total_amount() == 0
    assert TransactionQuery(session).received_by_user(user1).get_total_amount() == 0
    assert TransactionQuery(session).received_by_user(user2).get_total_amount() == 20
    assert TransactionQuery(session).received_by_user(user3).get_total_amount() == 60
    assert RetireQuery(session).belongs_to(user1).get_total_amount() == 20
    assert RetireQuery(session).belongs_to(user2).get_total_amount() == 0
    assert RetireQuery(session).belongs_to(user3).get_total_amount() == 0
    assert RetireQuery(session).is_retired_to_gsrn(meteringpoint1.gsrn).get_total_amount() == 10
    assert RetireQuery(session).is_retired_to_gsrn(meteringpoint2.gsrn).get_total_amount() == 10

    # -- ACT -----------------------------------------------------------------

    batch2.on_rollback()
    session.commit()

    # -- ASSERT --------------------------------------------------------------

    assert GgoQuery(session).belongs_to(user1).is_stored().get_total_amount() == 145
    assert GgoQuery(session).belongs_to(user2).is_stored().get_total_amount() == 10
    assert GgoQuery(session).belongs_to(user3).is_stored().get_total_amount() == 30
    assert TransactionQuery(session).sent_by_user(user1).get_total_amount() == 40
    assert TransactionQuery(session).sent_by_user(user2).get_total_amount() == 0
    assert TransactionQuery(session).sent_by_user(user3).get_total_amount() == 0
    assert TransactionQuery(session).received_by_user(user1).get_total_amount() == 0
    assert TransactionQuery(session).received_by_user(user2).get_total_amount() == 10
    assert TransactionQuery(session).received_by_user(user3).get_total_amount() == 30
    assert RetireQuery(session).belongs_to(user1).get_total_amount() == 15
    assert RetireQuery(session).belongs_to(user2).get_total_amount() == 0
    assert RetireQuery(session).belongs_to(user3).get_total_amount() == 0
    assert RetireQuery(session).is_retired_to_gsrn(meteringpoint1.gsrn).get_total_amount() == 5
    assert RetireQuery(session).is_retired_to_gsrn(meteringpoint2.gsrn).get_total_amount() == 10
