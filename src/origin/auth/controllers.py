import marshmallow_dataclass as md
from datetime import datetime, timezone

from origin import logger
from origin.db import atomic, inject_session
from origin.http import Controller, redirect, BadRequest
from origin.pipelines import start_import_meteringpoints
from origin.cache import redis
from origin.services.datahub import DataHubService

from .queries import UserQuery
from .backend import AuthBackend
from .models import (
    User,
    LoginRequest,
    VerifyLoginCallbackRequest,
    OnMeteringPointsAvailableWebhookRequest,
)


backend = AuthBackend()


class Login(Controller):
    """
    TODO
    """
    METHOD = 'GET'

    Request = md.class_schema(LoginRequest)

    def handle_request(self, request):
        """
        :param LoginRequest request:
        :rtype: flask.Response
        """
        login_url, state = backend.register_login_state()

        redis.set(state, request.return_url, ex=3600)

        return redirect(login_url, code=303)


class LoginCallback(Controller):
    """
    TODO
    """
    METHOD = 'GET'

    Request = md.class_schema(VerifyLoginCallbackRequest)

    datahub = DataHubService()

    @atomic
    def handle_request(self, request, session):
        """
        :param VerifyLoginCallbackRequest request:
        :param Session session:
        :rtype: flask.Response
        """
        return_url = redis.get(request.state)

        if return_url is None:
            raise BadRequest('Click back in your browser')
        else:
            return_url = return_url.decode()
            redis.delete(request.state)

        # Fetch token
        try:
            token = backend.fetch_token(request.code, request.state)
        except:
            logger.exception(f'Failed to fetch token', extra={
                'scope': str(request.scope),
                'code': request.code,
                'state': request.state,
            })
            return self.redirect_to_failure(return_url)

        # Extract data from token
        id_token = backend.get_id_token(token)

        # No id_token means the user declined to give consent
        if id_token is None:
            return self.redirect_to_failure(return_url, 'No ID token from Hydra')

        expires = datetime \
            .fromtimestamp(token['expires_at']) \
            .replace(tzinfo=timezone.utc)

        # Lookup user from "subject"
        user = UserQuery(session) \
            .has_sub(id_token['sub']) \
            .one_or_none()

        if user is None:
            logger.error(f'Creating new user and subscribing to webhooks', extra={
                'subject': id_token['sub'],
            })
            self.create_new_user(token, id_token, expires, session)
            self.datahub.webhook_on_meteringpoints_available_subscribe(token['access_token'])
            self.datahub.webhook_on_ggos_issued_subscribe(token['access_token'])
        else:
            logger.error(f'Updating tokens for existing user', extra={
                'subject': id_token['sub'],
            })
            self.update_user_attributes(user, token, expires)

        # Create HTTP response
        response = redirect(f'{return_url}?success=1', code=303)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['Cache-Control'] = 'public, max-age=0'

        return response

    def create_new_user(self, token, id_token, expires, session):
        """

        """
        user = User(
            sub=id_token['sub'],
            access_token=token['access_token'],
            refresh_token=token['refresh_token'],
            token_expire=expires,
        )

        user.set_key_from_entropy(f'{user.sub}TODO ENTROPY TODO ENTROPY TODO ENTROPY TODO ENTROPY')

        session.add(user)
        session.flush()

    def update_user_attributes(self, user, token, expires):
        """

        """
        user.access_token = token['access_token']
        user.refresh_token = token['refresh_token']
        user.token_expire = expires

    def redirect_to_failure(self, return_url, msg=''):
        """
        :param str return_url:
        :rtype: flask.Response
        """
        return redirect(f'{return_url}?success=0&msg={msg}', code=303)


class OnMeteringPointsAvailableWebhook(Controller):
    """
    TODO
    """
    Request = md.class_schema(OnMeteringPointsAvailableWebhookRequest)

    @inject_session
    def handle_request(self, request, session):
        """
        :param OnMeteringPointsAvailableWebhookRequest request:
        :param Session session:
        :rtype: bool
        """
        user = UserQuery(session) \
            .has_sub(request.sub) \
            .one_or_none()

        if user:
            start_import_meteringpoints(user)
            return True
        else:
            return False
