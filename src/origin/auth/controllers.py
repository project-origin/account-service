import os
import marshmallow_dataclass as md
from datetime import datetime, timezone

from origin import logger
from origin.db import atomic, inject_session
from origin.http import Controller, redirect, BadRequest
from origin.cache import redis
from origin.webhooks import validate_hmac
from origin.services.datahub import (
    DataHubService,
    MeteringPointType as DataHubMeteringPointType,
)
from origin.pipelines import (
    start_import_meteringpoints_for,
    start_send_key_to_datahub_service,
)

from .token import Token
from .decorators import require_oauth, inject_token, inject_user
from .queries import UserQuery, MeteringPointQuery
from .backend import AuthBackend
from .models import (
    User,
    Account,
    MeteringPoint,
    MeteringPointType,
    LoginRequest,
    VerifyLoginCallbackRequest,
    GetAccountsResponse,
    OnMeteringPointsAvailableWebhookRequest,
    OnMeteringPointAvailableWebhookRequest,
    FindSuppliersRequest,
    FindSuppliersResponse,
)
from ..common import DateTimeRange

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
            .is_active() \
            .has_sub(id_token['sub']) \
            .one_or_none()

        if user is None:
            logger.error(f'User login: Creating new user and subscribing to webhooks', extra={
                'subject': id_token['sub'],
            })
            self.create_new_user(token, id_token, expires, session)
            self.datahub.webhook_on_meteringpoint_available_subscribe(token['access_token'])
            self.datahub.webhook_on_ggo_issued_subscribe(token['access_token'])
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


class DisableUser(Controller):
    """
    Disables a user (permanently).
    """

    @require_oauth('profile')
    @inject_token
    def handle_request(self, token):
        """
        :param Token token:
        :rtype: bool
        """
        self.disable_user(token.subject)
        return True

    @atomic
    def disable_user(self, subject, session):
        """
        :param str subject:
        :param sqlalchemy.orm.Session session:
        """
        UserQuery(session) \
            .has_sub(subject) \
            .update({'disabled': True})


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


class FindSuppliers(Controller):
    """
    TODO
    """
    Request = md.class_schema(FindSuppliersRequest)
    Response = md.class_schema(FindSuppliersResponse)

    @require_oauth('profile')
    @inject_user
    def handle_request(self, request, user):
        """
        :param FindSuppliersRequest request:
        :param User user:
        :rtype: GetAccountsResponse
        """
        begin_range = DateTimeRange.from_date_range(request.date_range)

        users = list(self.find_suppliers(
            begin_from=begin_range.begin,
            begin_to=begin_range.end,
            min_amount=request.min_amount,
            min_coverage=request.min_coverage,
            exclude_user_id=user.id,
        ))

        return FindSuppliersResponse(
            success=True,
            suppliers=[u.sub for u in users],
        )

    @inject_session
    def find_suppliers(self, begin_from, begin_to, min_amount,
                       min_coverage, exclude_user_id, session):
        """
        TODO

        :param datetime begin_from:
        :param datetime begin_to:
        :param int min_amount:
        :param float min_coverage:
        :param int exclude_user_id:
        :param sqlalchemy.orm.Session session:
        :rtype: collections.abc.Iterable[User]
        """
        sql_params = {
            'begin_from': begin_from,
            'begin_to': begin_to,
            'min_amount': min_amount,
            'min_coverage': min_coverage,
            'exclude_user_id': exclude_user_id,
        }

        sql = """
            select user_id from (
                select
                       x.user_id,
                       count(x.amount) as distinct_begins,
                       count(x.amount) filter (where x.amount >= :min_amount) as eligible_begins
                from (
                       select ggo_ggo.user_id, sum(ggo_ggo.amount) as amount
                       from ggo_ggo
                       where ggo_ggo.stored = 't'
                       and ggo_ggo.begin >= :begin_from
                       and ggo_ggo.begin < :begin_to
                       and ggo_ggo.user_id != :exclude_user_id
                       group by ggo_ggo.user_id, ggo_ggo.begin
                   ) AS x
                group by 1
                order by 2 desc
            ) as y
            where cast(eligible_begins as float) / distinct_begins >= :min_coverage
            order by eligible_begins desc;
        """

        res = session.execute(sql, sql_params)

        for row in res:
            yield UserQuery(session) \
                .is_active() \
                .has_id(row[0]) \
                .one()


class OnMeteringPointAvailableWebhook(Controller):
    """
    Webhook invoked by DataHubService once new MeteringPoints are available.

    Starts an asynchronous pipeline to import them.
    """
    Request = md.class_schema(OnMeteringPointAvailableWebhookRequest)

    @validate_hmac
    @inject_session
    def handle_request(self, request, session):
        """
        :param OnMeteringPointAvailableWebhookRequest request:
        :param sqlalchemy.orm.Session session:
        :rtype: bool
        """
        user = UserQuery(session) \
            .is_active() \
            .has_sub(request.sub) \
            .one_or_none()

        # User exists?
        if user is None:
            logger.error(f'Can not import MeteringPoint (user not found in DB)', extra={
                'subject': request.sub,
                'gsrn': request.meteringpoint.gsrn,
            })
            return False

        # MeteringPoint already present in database?
        if self.meteringpoint_exists(request.meteringpoint.gsrn, session):
            logger.info(f'MeteringPoint {request.meteringpoint.gsrn} already exists in DB, skipping...', extra={
                'subject': user.sub,
                'gsrn': request.meteringpoint.gsrn,
            })
            return True

        # Insert new MeteringPoint in to DB
        meteringpoint = self.create_meteringpoint(user, request.meteringpoint)

        logger.info(f'Imported MeteringPoint with GSRN: {meteringpoint.gsrn}', extra={
            'subject': user.sub,
            'gsrn': meteringpoint.gsrn,
            'type': meteringpoint.type.value,
            'meteringpoint_id': meteringpoint.id,
        })

        # Send ledger key to DataHubService
        start_send_key_to_datahub_service(user.sub, meteringpoint.gsrn)

        return True

    def meteringpoint_exists(self, gsrn, session):
        """
        :param str gsrn:
        :param sqlalchemy.orm.Session session:
        :rtype: bool
        """
        count = MeteringPointQuery(session) \
            .has_gsrn(gsrn) \
            .count()

        return count > 0

    @atomic
    def create_meteringpoint(self, user, imported_meteringpoint, session):
        """
        :param origin.auth.User user:
        :param origin.services.datahub.MeteringPoint imported_meteringpoint:
        :param sqlalchemy.orm.Session session:
        :rtype: MeteringPoint
        """
        meteringpoint = MeteringPoint.create(
            user=user,
            gsrn=imported_meteringpoint.gsrn,
            sector=imported_meteringpoint.sector,
            type=self.get_type(imported_meteringpoint),
            session=session,
        )

        session.add(meteringpoint)
        session.flush()

        return meteringpoint

    def get_type(self, imported_meteringpoint):
        """
        :param origin.services.datahub.MeteringPoint imported_meteringpoint:
        :rtype: MeteringPointType
        """
        if imported_meteringpoint.type is DataHubMeteringPointType.PRODUCTION:
            return MeteringPointType.PRODUCTION
        elif imported_meteringpoint.type is DataHubMeteringPointType.CONSUMPTION:
            return MeteringPointType.CONSUMPTION
        else:
            raise RuntimeError('Should NOT have happened!')


class OnMeteringPointsAvailableWebhook(Controller):
    """
    Webhook invoked by DataHubService once new MeteringPoints are available.

    Starts an asynchronous pipeline to import them.

    TODO REMOVE THIS OLD ENDPOINT
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
            .is_active() \
            .has_sub(request.sub) \
            .one_or_none()

        if user:
            start_import_meteringpoints_for(user.sub)
            return True
        else:
            return False
