import os
import logging
from datetime import timedelta


DEBUG = os.environ.get('DEBUG') in ('1', 't', 'true', 'yes')

# -- Project -----------------------------------------------------------------

PROJECT_NAME = 'Account Service'
SERVICE_NAME = os.environ['SERVICE_NAME']
SECRET = os.environ['SECRET']
PROJECT_URL = os.environ['PROJECT_URL']
LOGIN_CALLBACK_URL = f'{PROJECT_URL}/auth/login/callback'
CORS_ORIGINS = os.environ['CORS_ORIGINS']

_LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG')

if hasattr(logging, _LOG_LEVEL):
    LOG_LEVEL = getattr(logging, _LOG_LEVEL)
else:
    raise ValueError('Invalid LOG_LEVEL: %s' % _LOG_LEVEL)


# -- Database ----------------------------------------------------------------

SQL_ALCHEMY_SETTINGS = {
    'echo': False,
    'pool_pre_ping': True,
    'pool_size': int(os.environ['DATABASE_CONN_POLL_SIZE']),
}

DATABASE_URI = os.environ['DATABASE_URI']


# -- Services ----------------------------------------------------------------

DATAHUB_SERVICE_URL = os.environ['DATAHUB_SERVICE_URL']
LEDGER_URL = os.environ['LEDGER_URL']
ENERGY_TYPE_SERVICE_URL = os.environ['ENERGY_TYPE_SERVICE_URL']


# -- webhook -----------------------------------------------------------------

HMAC_HEADER = 'x-hub-signature'
WEBHOOK_SECRET = os.environ['WEBHOOK_SECRET']


# -- Auth/tokens -------------------------------------------------------------

TOKEN_HEADER = 'Authorization'

# Access tokens will be refreshed when their expire time
# is less than this:
TOKEN_REFRESH_AT = timedelta(minutes=60 * 24)

HYDRA_URL = os.environ['HYDRA_URL']
HYDRA_INTROSPECT_URL = os.environ['HYDRA_INTROSPECT_URL']
HYDRA_CLIENT_ID = os.environ['HYDRA_CLIENT_ID']
HYDRA_CLIENT_SECRET = os.environ['HYDRA_CLIENT_SECRET']
HYDRA_AUTH_ENDPOINT = f'{HYDRA_URL}/oauth2/auth'
HYDRA_TOKEN_ENDPOINT = f'{HYDRA_URL}/oauth2/token'
HYDRA_WELLKNOWN_ENDPOINT = f'{HYDRA_URL}/.well-known/jwks.json'
HYDRA_USER_ENDPOINT = f'{HYDRA_URL}/userinfo'
HYDRA_WANTED_SCOPES = (
    'openid',
    'offline',
    'profile',
    'email',
    'disclosure',
    'meteringpoints.read',
    'measurements.read',
    'ggo.read',
    'ggo.transfer',
    'ggo.retire',
)


# -- Task broker and locking -------------------------------------------------

REDIS_HOST = os.environ['REDIS_HOST']
REDIS_PORT = int(os.environ['REDIS_PORT'])
REDIS_USERNAME = os.environ['REDIS_USERNAME']
REDIS_PASSWORD = os.environ['REDIS_PASSWORD']
REDIS_CACHE_DB = int(os.environ['REDIS_CACHE_DB'])
REDIS_BROKER_DB = int(os.environ['REDIS_BROKER_DB'])
REDIS_BACKEND_DB = int(os.environ['REDIS_BACKEND_DB'])

REDIS_URL = 'redis://%s:%s@%s:%d' % (
    REDIS_USERNAME, REDIS_PASSWORD, REDIS_HOST, REDIS_PORT)

REDIS_BROKER_URL = '%s/%d' % (REDIS_URL, REDIS_BROKER_DB)
REDIS_BACKEND_URL = '%s/%d' % (REDIS_URL, REDIS_BACKEND_DB)


# -- Misc --------------------------------------------------------------------

AZURE_APP_INSIGHTS_CONN_STRING = os.environ.get('AZURE_APP_INSIGHTS_CONN_STRING')

UNKNOWN_TECHNOLOGY_LABEL = 'Unknown'

BATCH_RESUBMIT_AFTER_HOURS = 6
