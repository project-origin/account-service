import os
from datetime import timedelta


DEBUG = os.environ.get('DEBUG') in ('1', 't', 'true', 'yes')

# -- Project -----------------------------------------------------------------

PROJECT_NAME = 'Project Origin AccountService'

PROJECT_URL = os.environ.get(
    'PROJECT_URL', 'http://127.0.0.1:8085')

LOGIN_CALLBACK_URL = f'{PROJECT_URL}/auth/login/callback'


# -- Directories/paths -------------------------------------------------------

__current_file = os.path.abspath(__file__)
__current_folder = os.path.split(__current_file)[0]

PROJECT_DIR = os.path.abspath(os.path.join(__current_folder, '..', '..'))
VAR_DIR = os.path.join(PROJECT_DIR, 'var')
SOURCE_DIR = os.path.join(PROJECT_DIR, 'src')
MIGRATIONS_DIR = os.path.join(SOURCE_DIR, 'migrations')
ALEMBIC_CONFIG_PATH = os.path.join(MIGRATIONS_DIR, 'alembic.ini')


# -- Database ----------------------------------------------------------------

SQL_ALCHEMY_SETTINGS = {
    'echo': DEBUG and 0,
    'pool_pre_ping': True,
    'pool_size': 20,
}
SQLITE_PATH = os.path.join(VAR_DIR, 'db.sqlite')
TEST_SQLITE_PATH = os.path.join(VAR_DIR, 'db.test.sqlite')
# DATABASE_URI = os.environ.get('DATABASE_URI', 'sqlite:///%s' % SQLITE_PATH)
DATABASE_URI = os.environ.get('DATABASE_URI', 'postgresql://postgres:1234@172.17.0.2/account')

USING_POSTGRES = DATABASE_URI.startswith('postgresql://')
USING_SQLITE = DATABASE_URI.startswith('sqlite://')


# -- Services ----------------------------------------------------------------

DATAHUB_SERVICE_URL = os.environ.get(
    'DATAHUB_SERVICE_URL', 'http://127.0.0.1:8089')

LEDGER_URL = os.environ.get(
    'LEDGER_URL', 'http://127.0.0.1:8008')


# -- Auth/tokens -------------------------------------------------------------

TOKEN_HEADER = 'Authorization'

# Access tokens will be refreshed when their expire time
# is less than this:
TOKEN_REFRESH_AT = timedelta(minutes=60 * 24)

HYDRA_URL = os.environ.get('HYDRA_URL', 'https://localhost:9100')
HYDRA_INTROSPECT_URL = os.environ.get('HYDRA_INTROSPECT_URL', 'https://localhost:9101/oauth2/introspect')
HYDRA_CLIENT_ID = os.environ.get('HYDRA_CLIENT_ID', 'account_service')
HYDRA_CLIENT_SECRET = os.environ.get('HYDRA_CLIENT_SECRET', 'some-secret')
HYDRA_AUTH_ENDPOINT = f'{HYDRA_URL}/oauth2/auth'
HYDRA_TOKEN_ENDPOINT = f'{HYDRA_URL}/oauth2/token'
HYDRA_USER_ENDPOINT = f'{HYDRA_URL}/userinfo'
HYDRA_WANTED_SCOPES = (
    'openid',
    'offline',
    'profile',
    'email',
    'meteringpoints.read',
    'measurements.read',
    'ggo.read',
    'ggo.transfer',
    'ggo.retire',
)


# -- Task broker and locking -------------------------------------------------

REDIS_HOST = os.environ.get('REDIS_HOST', '172.17.0.3')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_USERNAME = os.environ.get('REDIS_USERNAME', '')
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', '')
REDIS_CACHE_DB = int(os.environ.get('REDIS_CACHE_DB', 3))
REDIS_BROKER_DB = int(os.environ.get('REDIS_BROKER_DB', 4))
REDIS_BACKEND_DB = int(os.environ.get('REDIS_BACKEND_DB', 5))

REDIS_URL = 'redis://%s:%s@%s:%d' % (
    REDIS_USERNAME, REDIS_PASSWORD, REDIS_HOST, REDIS_PORT)

REDIS_BROKER_URL = '%s/%d' % (REDIS_URL, REDIS_BROKER_DB)
REDIS_BACKEND_URL = '%s/%d' % (REDIS_URL, REDIS_BACKEND_DB)
