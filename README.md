![alt text](doc/logo.png)

# Project Origin AccountService

This is the repository for Project Origin's AccountService.

This service is responsible for:

- Keeps track of user's stored, retired, and transferred GGOs (ie. their "account")
- Exposing endpoints to transfer GGOs to other users
- Exposing endpoints to retire GGOs to any of the user's metering points
- Exposing endpoints to access information and statistics about user's account
- Submit transfers and retires to the blockchain ledger, and keep its database synchronized blockchain ledger


## Installation and running locally

The following sections describes how to install and run the project locally for development and debugging.


## Requirements

- Python 3.7
- Pip
- Pipenv
- A PostgreSQL server with one database
- A Redis server with tree databases
- A Unix/Linux machine

### First time installation


Initially, make sure to define necessary environment variables (listed below).
You can define them in the .env file in the root of the project
([more details on this here](https://pipenv-fork.readthedocs.io/en/latest/advanced.html#automatic-loading-of-env)).

Also, make sure to upgrade your system packages for good measure:
   
    pip install --upgrade --user setuptools pip pipenv

Then install project dependencies:

    pipenv install

Then apply database migrations:

    cd src/migrations
    pipenv run migrate
    cd ../../

### Running locally (development)

This starts the local development server (NOT for production use):

    pipenv run develop

### Running tests

Run unit- and integration tests:

    pipenv run pytest


## Environment variables

Name | Description | Example
:--- | :--- | :--- |
`SERVICE_NAME` | Name of this service | `ExampleBackend`
`DEBUG` | Whether or not to enable debugging mode (off by default) | `0` or `1`
`SECRET` | Application secret for misc. operations | `foobar`
`CORS_ORIGINS` | Allowed CORS origins | `http://www.example.com`
**URLs:** | |
`PROJECT_URL` | Public URL to this service without trailing slash | `https://account.projectorigin.dk`
`DATAHUB_SERVICE_URL` | Public URL to DataHubService without trailing slash | `https://datahub.projectorigin.dk`
`LEDGER_URL` | URL to Blockchain Ledger without trailing slash | `https://ledger.projectorigin.dk`
`ENERGY_TYPE_SERVICE_URL` | URL to EnergyTypeService Ledger without trailing slash | `https://energytype.projectorigin.dk`
**Webhooks:** | |
`WEBHOOK_SECRET` | The secret to post together with the webhooks. | `some-secret`
**Authentication:** | |
`HYDRA_URL` | URL to Hydra without trailing slash | `https://auth.projectorigin.dk`
`HYDRA_INTROSPECT_URL` | URL to Hydra Introspect without trailing slash | `https://authintrospect.projectorigin.dk`
`HYDRA_CLIENT_ID` | Hydra client ID | `account_service`
`HYDRA_CLIENT_SECRET` | Hydra client secret | `some-secret`
**Redis:** | |
`REDIS_HOST` | Redis hostname/IP | `127.0.0.1`
`REDIS_PORT` | Redis port number | `6379`
`REDIS_USERNAME` | Redis username | `johndoe`
`REDIS_PASSWORD` | Redis username | `qwerty`
`REDIS_CACHE_DB` | Redis database for caching (unique for this service) | `0`
`REDIS_BROKER_DB` | Redis database for task brokering (unique for this service) | `1`
`REDIS_BACKEND_DB` | Redis database for task results (unique for this service) | `2`
**Logging:** | |
`AZURE_APP_INSIGHTS_CONN_STRING` | Azure Application Insight connection string (optional) | `InstrumentationKey=19440978-19a8-4d07-9a99-b7a31d99f313`
**Database:** | |
`DATABASE_URI` | Database connection string for SQLAlchemy | `postgresql://scott:tiger@localhost/mydatabase`
`DATABASE_CONN_POLL_SIZE` | Connection pool size per container | `10`
**Runtime:** | |
`WORKERS` | Number of Gunicorn threads to run for the web API | `3`
`WORKER_CONNECTIONS` | Number of gevent greenthreads to run for each Gunicorn thread | `100`
`CONCURRENCY` | Number of gevent greenthreads to execute asynchronous tasks | `100`


## Building container image

    docker build -f Dockerfile -t account-service:v1 .

## Running container images

Web API:

    docker run --entrypoint /app/entrypoint.web.sh account-service:v1

Worker:

    docker run --entrypoint /app/entrypoint.worker.sh account-service:v1

Worker Beat:

    docker run --entrypoint /app/entrypoint.beat.sh account-service:v1

# System architecture

The following diagram depicts the overall architecture of AccountService and its dependencies. A few key points are listed below the diagram.

![alt text](doc/AccountService.png)

- It exposes a web API using OAuth2 authentication.
- It has one asynchronous worker running its own process (container).
- The web API process starts asynchronous tasks by submitting them to a distributed queue using Redis.
- A Beat process kicks off periodic tasks.


# 3rd party libraries

This project uses the following 3rd party libraries:

- [Flask](https://flask.palletsprojects.com/en/1.1.x/): HTTP framework
- [SQLAlchemy](https://www.sqlalchemy.org/): Database ORM
- [Alembic](https://alembic.sqlalchemy.org/en/latest/): Database migrations and revisioning
- [Marshmallow](https://marshmallow.readthedocs.io/en/stable/): JSON serialization/deserialization and validation
- [Celery](https://docs.celeryproject.org/): Asynchronous tasks
- [Redis](https://pypi.org/project/redis/): Celery backend + caching
- [OpenCensus](https://github.com/census-instrumentation/opencensus-python): Logging and tracing
- [Authlib](https://docs.authlib.org): OAuth2 implementation
- [Origin-Ledger-SDK](https://pypi.org/project/Origin-Ledger-SDK/): Interface with the blockchain ledger
- [bip32utils](https://github.com/lyndsysimon/bip32utils/): Generating block keys for the ledger
- [pytest](https://docs.pytest.org/): Testing
