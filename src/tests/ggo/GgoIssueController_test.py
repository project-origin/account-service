import pytest
import testing.postgresql
import marshmallow_dataclass as md
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta, timezone

from origin.db import ModelBase
from origin.auth import User, MeteringPoint
from origin.ggo import GgoIssueController, Ggo, GgoQuery
from origin.services.datahub import Ggo as DataHubGgo, GetGgoListResponse

from .import_ggo_data import IMPORT_GGO_DATA1


GGO_AMOUNT = 100


user = User(
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
def session():
    """
    Returns a Session object with Ggo + User data seeded for testing
    """
    with testing.postgresql.Postgresql() as psql:
        engine = create_engine(psql.url())
        ModelBase.metadata.create_all(engine)
        Session = sessionmaker(bind=engine, expire_on_commit=False)

        session = Session()
        session.add(user)
        session.flush()
        session.commit()
        session.add(MeteringPoint.create(
            user=user,
            session=session,
            gsrn='571313180400240049',
            sector='DK1',
        ))
        session.add(MeteringPoint.create(
            user=user,
            session=session,
            gsrn='GSRN2',
            sector='DK1',
        ))
        session.commit()
        yield session
        session.close()


# -- TEST CASES --------------------------------------------------------------


@patch('origin.ggo.issuing.datahub_service')
def test__GgoIssueController__fetch_ggos__invokes_datahub_with_correct_parameters(datahub_service):

    # Arrange
    gsrn = '123456789012345'
    begin_from = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    begin_to = datetime(2020, 12, 31, 23, 0, 0, tzinfo=timezone.utc)
    uut = GgoIssueController()

    # Act
    uut.fetch_ggos(user, gsrn, begin_from, begin_to)

    # Assert
    datahub_service.get_ggo_list.assert_called_once()
    assert datahub_service.get_ggo_list.call_args[0][0] == user.access_token
    assert datahub_service.get_ggo_list.call_args[0][1].gsrn == gsrn
    assert datahub_service.get_ggo_list.call_args[0][1].begin_range.begin == begin_from
    assert datahub_service.get_ggo_list.call_args[0][1].begin_range.end == begin_to


def test__GgoIssueController__map_imported_ggo__maps_Ggo_correctly():

    # Arrange
    imported_ggo = DataHubGgo(
        address='some-address-blabla',
        gsrn='654321987598761',
        begin=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        end=datetime(2020, 12, 31, 23, 0, 0, tzinfo=timezone.utc),
        sector='DK2',
        amount=123456,
        issue_time=datetime(2020, 2, 1, 0, 0, 0, tzinfo=timezone.utc),
        expire_time=datetime(2020, 5, 1, 0, 0, 0, tzinfo=timezone.utc),
        technology_code='T050505',
        fuel_code='F09090909',
    )

    uut = GgoIssueController()

    # Act
    mapped_ggo = uut.map_imported_ggo(user, imported_ggo)

    # Assert
    assert isinstance(mapped_ggo, Ggo)
    assert mapped_ggo.user_id == user.id
    assert mapped_ggo.address == imported_ggo.address
    assert mapped_ggo.issue_time == imported_ggo.issue_time
    assert mapped_ggo.expire_time == imported_ggo.expire_time
    assert mapped_ggo.begin == imported_ggo.begin
    assert mapped_ggo.end == imported_ggo.end
    assert mapped_ggo.amount == imported_ggo.amount
    assert mapped_ggo.sector == imported_ggo.sector
    assert mapped_ggo.technology_code == imported_ggo.technology_code
    assert mapped_ggo.fuel_code == imported_ggo.fuel_code
    assert mapped_ggo.issue_gsrn == imported_ggo.gsrn
    assert mapped_ggo.synchronized is True
    assert mapped_ggo.issued is True
    assert mapped_ggo.stored is True
    assert mapped_ggo.locked is False


@patch('origin.ggo.issuing.datahub_service')
def test__GgoIssueController__integration(datahub_service, session):

    def __get_ggo_list(access_token, request):
        datahub_response_schema = md.class_schema(GetGgoListResponse)
        datahub_response = datahub_response_schema()
        return datahub_response.loads(IMPORT_GGO_DATA1)

    # Arrange
    datahub_service.get_ggo_list.side_effect = __get_ggo_list
    begin_from = datetime(2020, 9, 1, 0, 0, tzinfo=timezone.utc)
    begin_to = datetime(2020, 9, 30, 23, 0, tzinfo=timezone.utc)
    uut = GgoIssueController()

    # Act
    uut.import_ggos(user, '571313180400240049', begin_from, begin_to, session)
    session.commit()

    # Assert
    query = GgoQuery(session).belongs_to(user)
    begins = query.get_distinct_begins()
    assert query.count() == 720
    assert min(begins).astimezone(timezone.utc) == datetime(2019, 9, 1, 0, 0, tzinfo=timezone.utc)
    assert max(begins).astimezone(timezone.utc) == datetime(2019, 9, 30, 23, 0, tzinfo=timezone.utc)

    # Second time should not do anything
    uut.import_ggos(user, '571313180400240049', begin_from, begin_to, session)
    session.commit()

    # Assert
    query = GgoQuery(session).belongs_to(user)
    begins = query.get_distinct_begins()
    assert query.count() == 720
    assert min(begins).astimezone(timezone.utc) == datetime(2019, 9, 1, 0, 0, tzinfo=timezone.utc)
    assert max(begins).astimezone(timezone.utc) == datetime(2019, 9, 30, 23, 0, tzinfo=timezone.utc)
