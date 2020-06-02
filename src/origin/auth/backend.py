import json
import requests
from authlib.jose import jwt
from authlib.integrations.requests_client import OAuth2Session

from origin import logger
from origin.cache import redis
from origin.settings import (
    DEBUG,
    LOGIN_CALLBACK_URL,
    HYDRA_AUTH_ENDPOINT,
    HYDRA_TOKEN_ENDPOINT,
    HYDRA_WELLKNOWN_ENDPOINT,
    HYDRA_CLIENT_ID,
    HYDRA_CLIENT_SECRET,
    HYDRA_WANTED_SCOPES,
)


class AuthBackend(object):
    """
    TODO
    """
    @property
    def client(self):
        """
        :rtype: OAuth2Session
        """
        return OAuth2Session(
            client_id=HYDRA_CLIENT_ID,
            client_secret=HYDRA_CLIENT_SECRET,
            scope=HYDRA_WANTED_SCOPES,
        )

    def register_login_state(self):
        """
        :rtype: (str, str)
        :returns: Tuple of (login_url, state)
        """
        try:
            return self.client.create_authorization_url(
                url=HYDRA_AUTH_ENDPOINT,
                redirect_uri=LOGIN_CALLBACK_URL,
            )
        except json.decoder.JSONDecodeError as e:
            logger.exception('JSONDecodeError from Hydra', extra={'doc': e.doc})
            raise

    def fetch_token(self, code, state):
        """
        :param str code:
        :param str state:
        :rtype: collections.abc.Mapping
        """
        try:
            return self.client.fetch_token(
                url=HYDRA_TOKEN_ENDPOINT,
                grant_type='authorization_code',
                code=code,
                state=state,
                redirect_uri=LOGIN_CALLBACK_URL,
                verify=not DEBUG,
            )
        except json.decoder.JSONDecodeError as e:
            logger.exception('JSONDecodeError from Hydra', extra={'doc': e.doc})
            raise

    def refresh_token(self, refresh_token):
        """
        :param str refresh_token:
        :rtype:
        """
        try:
            return self.client.refresh_token(
                url=HYDRA_TOKEN_ENDPOINT,
                refresh_token=refresh_token,
                verify=not DEBUG,
            )
        except json.decoder.JSONDecodeError as e:
            logger.exception('JSONDecodeError from Hydra', extra={'doc': e.doc})
            raise

    def get_id_token(self, token):
        """
        :param collections.abc.Mapping token:
        :rtype: collections.abc.Mapping
        """
        if 'id_token' in token:
            return jwt.decode(token['id_token'], key=self.get_jwks())
        else:
            return None

    def get_jwks(self):
        """
        TODO cache?

        :rtype: str
        """
        jwks = redis.get('HYDRA_JWKS')

        if jwks is None:
            jwks_response = requests.get(url=HYDRA_WELLKNOWN_ENDPOINT, verify=not DEBUG)
            jwks = jwks_response.content
            redis.set('HYDRA_JWKS', jwks.decode(), ex=3600)

        return jwks.decode()
