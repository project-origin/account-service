"""
conftest.py according to pytest docs:
https://docs.pytest.org/en/2.7.3/plugins.html?highlight=re#conftest-py-plugins
"""
import pytest
import testing.postgresql
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from origin.db import ModelBase


# @pytest.fixture(scope='function')
# def session():
#     with testing.postgresql.Postgresql() as psql:
#         engine = create_engine(psql.url())
#         ModelBase.metadata.create_all(engine)
#         Session = sessionmaker(bind=engine, expire_on_commit=False)
#         session = Session()
#
#         yield session
#
#         session.close()


@pytest.fixture(scope='function')
def session(postgresql_db):
    """
    Returns a Session object with Ggo + User data seeded for testing
    """
    ModelBase.metadata.create_all(postgresql_db.engine)
    Session = sessionmaker(bind=postgresql_db.engine, expire_on_commit=False)
    session = Session()

    yield session

    session.close()
