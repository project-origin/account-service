"""
conftest.py according to pytest docs:
https://docs.pytest.org/en/2.7.3/plugins.html?highlight=re#conftest-py-plugins
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from celery.backends.redis import RedisBackend
from testcontainers.general import DockerContainer
from testcontainers.postgres import PostgresContainer

from origin.db import ModelBase
from origin.tasks import celery_app


@pytest.fixture(scope='module')
def session():
    with PostgresContainer('postgres:9.6') as psql:
        engine = create_engine(psql.get_connection_url())
        ModelBase.metadata.create_all(engine)
        Session = sessionmaker(bind=engine, expire_on_commit=False)

        session = Session()
        yield session
        session.close()


@pytest.fixture(scope='module')
def redis():
    with DockerContainer('redis:latest').with_bind_ports(6379, 6380) as container:
        yield (
            container.get_container_host_ip(),
            container.get_exposed_port(6379)
        )


@pytest.fixture(scope='module')
def celery_config(redis):
    redis_host, redis_port = redis
    redis_url = f'redis://:@{redis_host}:{redis_port}'

    return {
        'broker_url': f'{redis_url}/0',
        'result_backend': f'{redis_url}/1',
    }
