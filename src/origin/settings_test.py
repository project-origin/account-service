import os
from datetime import timedelta


DEBUG = True

# -- Project -----------------------------------------------------------------

PROJECT_NAME = 'Account Service'
SERVICE_NAME = 'AccountService'
SECRET = None
PROJECT_URL = None
LOGIN_CALLBACK_URL = f'{PROJECT_URL}/auth/login/callback'
CORS_ORIGINS = None


# -- Database ----------------------------------------------------------------

SQL_ALCHEMY_SETTINGS = {}
DATABASE_URI = None


# -- Services ----------------------------------------------------------------

DATAHUB_SERVICE_URL = None
LEDGER_URL = None
ENERGY_TYPE_SERVICE_URL = None


# -- webhook -----------------------------------------------------------------

HMAC_HEADER = 'x-hub-signature'
WEBHOOK_SECRET = None


# -- Auth/tokens -------------------------------------------------------------

TOKEN_HEADER = 'Authorization'

# Access tokens will be refreshed when their expire time
# is less than this:
TOKEN_REFRESH_AT = timedelta(minutes=60 * 24)

HYDRA_URL = None
HYDRA_INTROSPECT_URL = None
HYDRA_CLIENT_ID = None
HYDRA_CLIENT_SECRET = None
HYDRA_AUTH_ENDPOINT = None
HYDRA_TOKEN_ENDPOINT = None
HYDRA_WELLKNOWN_ENDPOINT = None
HYDRA_USER_ENDPOINT = None
HYDRA_WANTED_SCOPES = None


# -- Task broker and locking -------------------------------------------------

REDIS_HOST = None
REDIS_PORT = None
REDIS_USERNAME = None
REDIS_PASSWORD = None
REDIS_CACHE_DB = None
REDIS_BROKER_DB = None
REDIS_BACKEND_DB = None

REDIS_URL = None

REDIS_BROKER_URL = None
REDIS_BACKEND_URL = None


# -- Misc --------------------------------------------------------------------

AZURE_APP_INSIGHTS_CONN_STRING = None

UNKNOWN_TECHNOLOGY_LABEL = 'Unknown'

BATCH_RESUBMIT_AFTER_HOURS = 6
