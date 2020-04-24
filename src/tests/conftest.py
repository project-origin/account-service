"""
conftest.py according to pytest docs:
https://docs.pytest.org/en/2.7.3/plugins.html?highlight=re#conftest-py-plugins
"""
import os
import pytest
from uuid import uuid4
from unittest.mock import Mock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from origin.db import ModelBase
from origin.settings import TEST_SQLITE_PATH
from origin.auth import User


@pytest.fixture(scope='function')
def session():
    """
    Creates a new empty database and applies the database schema on it.
    When test is complete, deletes the database file to start over
    in the next test.

    If one wants to use an actual PostgreSQL/MySQL database for testing
    in stead of SQLite, using testing.postgresql or testing.mysql,
    this can be implemented in the setup/teardown here.
    """

    # Setup
    if os.path.isfile(TEST_SQLITE_PATH):
        os.remove(TEST_SQLITE_PATH)

    test_db_uri = 'sqlite:///%s' % TEST_SQLITE_PATH
    engine = create_engine(test_db_uri, echo=False)
    ModelBase.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = scoped_session(factory)()

    # Yield session executes the dependent test/fixture
    yield session

    # Teardown
    session.close()
    os.remove(TEST_SQLITE_PATH)


# -- Users -------------------------------------------------------------------

@pytest.fixture(scope='function')
def user1():
    """
    :return User:
    """
    return User(
        id=1,
        oid='9647fa5c-56e3-4f35-942c-9357b45f2b92',
        account_number='47cca5f5-e198-4f29-a234-c221a8aa6b82',
    )


@pytest.fixture(scope='function')
def user2():
    """
    :return User:
    """
    return User(
        id=2,
        oid='d0ecc9f0-a050-440e-b324-70be8ccc33fe',
        account_number='1a6fc561-2e10-4604-a703-bda115485e80',
    )
