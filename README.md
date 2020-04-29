![alt text](doc/logo.png)

# Project Origin AccountService

TODO Describe the project here


# Environment variables

Name | Description | Example
:--- | :--- | :--- |
`DEBUG` | Whether or not to enable debugging mode (off by default) | `0` or `1`
`SECRET` | Application secret for misc. operations | `foobar`
`DATABASE_URI` | Database connection string for SQLAlchemy | `postgresql://scott:tiger@localhost/mydatabase`
`DATABASE_CONN_POLL_SIZE` | Connection pool size per container | `10`
`CORS_ORIGINS` | Allowed CORS origins | `http://www.example.com`
**URLs:** | |
`PROJECT_URL` | Public URL to this service without trailing slash | `https://account.projectorigin.dk`
`DATAHUB_SERVICE_URL` | Public URL to DataHubService without trailing slash | `https://datahub.projectorigin.dk`
`LEDGER_URL` | URL to Blockchain Ledger without trailing slash | `https://ledger.projectorigin.dk`
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


# Building container images

Web API:

    sudo docker build -f Dockerfile.web -t account-service-web:v1 .

Worker:

    sudo docker build -f Dockerfile.worker -t account-service-worker:v1 .

Worker Beat:

    sudo docker build -f Dockerfile.beat -t account-service-beat:v1 .
