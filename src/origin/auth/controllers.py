import os
import marshmallow_dataclass as md
from datetime import datetime, timezone

from origin import logger
from origin.db import atomic, inject_session
from origin.http import Controller, redirect, BadRequest
from origin.pipelines import start_import_meteringpoints
from origin.cache import redis
from origin.services.datahub import DataHubService
from origin.webhooks import validate_hmac

from .token import Token
from .decorators import require_oauth, inject_token
from .queries import UserQuery
from .backend import AuthBackend
from .models import (
    User,
    Account,
    LoginRequest,
    VerifyLoginCallbackRequest,
    OnMeteringPointsAvailableWebhookRequest,
    GetAccountsResponse,
)


backend = AuthBackend()


class Login(Controller):
    """
    Redirects the client to the authentication server to perform
    authentication and grant necessary permissions (possibly signing
    up and activating their account for the first time).
    The redirect URL contains login tokens unique for, and personal to,
    the client, and should never be reused.

    Upon completing the login flow, the client is redirected back to
    AccountService, which creates an account in its own database (if
    one not already exists for the user) before redirecting the client
    back to the provided returnUrl.
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
    Callback for when authentication is complete.

    Creates that user if not already present in databse (identified by the
    subject, which is generated by the authentication service).
    """
    METHOD = 'GET'

    Request = md.class_schema(VerifyLoginCallbackRequest)

    datahub = DataHubService()

    @atomic
    def handle_request(self, request, session):
        """
        :param VerifyLoginCallbackRequest request:
        :param sqlalchemy.orm.Session session:
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
            logger.error(f'User login: Creating new user and subscribing to webhooks', extra={
                'subject': id_token['sub'],
            })
            self.create_new_user(token, id_token, expires, session)
            self.datahub.webhook_on_meteringpoints_available_subscribe(token['access_token'])
            self.datahub.webhook_on_ggos_issued_subscribe(token['access_token'])
        else:
            logger.error(f'User login: Updating tokens for existing user', extra={
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
        Create a new user.
        """
        user = User(
            sub=id_token['sub'],
            access_token=token['access_token'],
            refresh_token=token['refresh_token'],
            token_expire=expires,
        )

        entropy = os.urandom(256) + user.sub.encode()
        user.set_key_from_entropy(entropy)
        user.update_last_login()

        session.add(user)
        session.flush()

    def update_user_attributes(self, user, token, expires):
        """
        Updates token for an existing user.
        """
        user.update_last_login()
        user.access_token = token['access_token']
        user.refresh_token = token['refresh_token']
        user.token_expire = expires

    def redirect_to_failure(self, return_url, msg=''):
        """
        :param str return_url:
        :rtype: flask.Response
        """
        return redirect(f'{return_url}?success=0&msg={msg}', code=303)


class GetAccounts(Controller):
    """
    Returns a list of the user's account IDs.
    These are the IDs to use when transferring GGOs between users.
    """
    Response = md.class_schema(GetAccountsResponse)

    @require_oauth('profile')
    @inject_token
    def handle_request(self, token):
        """
        :param Token token:
        :rtype: GetAccountsResponse
        """
        return GetAccountsResponse(
            success=True,
            accounts=[Account(id=token.subject)],
        )


class OnMeteringPointsAvailableWebhook(Controller):
    """
    Webhook invoked by DataHubService once new MeteringPoints are available.

    Starts an asynchronous pipeline to import them.
    """
    Request = md.class_schema(OnMeteringPointsAvailableWebhookRequest)

    @validate_hmac
    @inject_session
    def handle_request(self, request, session):
        """
        :param OnMeteringPointsAvailableWebhookRequest request:
        :param sqlalchemy.orm.Session session:
        :rtype: bool
        """
        user = UserQuery(session) \
            .has_sub(request.sub) \
            .one_or_none()

        if user:
            start_import_meteringpoints(user.sub)
            return True
        else:
            return False
