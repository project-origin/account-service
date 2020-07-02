from datetime import timezone

import marshmallow_dataclass as md

from origin.db import inject_session, atomic
from origin.http import Controller, BadRequest
from origin.webhooks import validate_hmac
from origin.pipelines import (
    start_handle_composed_ggo_pipeline,
    start_invoke_on_ggo_received_tasks,
)
from origin.auth import (
    User,
    UserQuery,
    MeteringPointQuery,
    MeteringPoint,
    inject_user,
    require_oauth,
)

from .composer import GgoComposer
from .queries import GgoQuery, TransactionQuery
from .models import (
    Ggo,
    TransferDirection,
    TransferRequest,
    RetireRequest,
    GetGgoListRequest,
    GetGgoListResponse,
    GetGgoSummaryRequest,
    GetGgoSummaryResponse,
    GetTotalAmountRequest,
    GetTotalAmountResponse,
    GetTransferSummaryRequest,
    GetTransferSummaryResponse,
    GetTransferredAmountRequest,
    GetTransferredAmountResponse,
    ComposeGgoRequest,
    ComposeGgoResponse,
    OnGgosIssuedWebhookRequest,
)


class GetGgoList(Controller):
    """
    Returns a list of GGO objects which belongs to the account. The database
    contains a historical record of prior received, sent, and retired GGOs,
    so this endpoint will return GGOs that are no longer available,
    unless filtered out.
    """
    Request = md.class_schema(GetGgoListRequest)
    Response = md.class_schema(GetGgoListResponse)

    @require_oauth('ggo.read')
    @inject_user
    @inject_session
    def handle_request(self, request, user, session):
        """
        :param GetGgoListRequest request:
        :param User user:
        :param sqlalchemy.orm.Session session:
        :rtype: GetGgoListResponse
        """
        query = GgoQuery(session) \
            .belongs_to(user) \
            .is_synchronized(True) \
            .is_locked(False) \
            .apply_filters(request.filters)

        results = query \
            .order_by(Ggo.begin) \
            .offset(request.offset)

        if request.limit:
            results = results.limit(request.limit)

        return GetGgoListResponse(
            success=True,
            total=query.count(),
            results=results.all(),
        )


class GetGgoSummary(Controller):
    """
    Returns a summary of the account's GGOs, or a subset hereof.
    Useful for plotting or visualizing data.

    TODO resolutionIso: https://www.digi.com/resources/documentation/digidocs/90001437-13/reference/r_iso_8601_duration_format.htm
    """
    Request = md.class_schema(GetGgoSummaryRequest)
    Response = md.class_schema(GetGgoSummaryResponse)

    @require_oauth('ggo.read')
    @inject_user
    @inject_session
    def handle_request(self, request, user, session):
        """
        :param GetGgoSummaryRequest request:
        :param User user:
        :param sqlalchemy.orm.Session session:
        :rtype: GetGgoSummaryResponse
        """
        summary = GgoQuery(session) \
            .belongs_to(user) \
            .apply_filters(request.filters) \
            .get_summary(request.resolution, request.grouping)

        # client_date = self.get_client_date()
        # a = request.filters.begin_range.begin
        # b = request.filters.begin_range.begin.astimezone(timezone.utc)

        # raise Exception(str(query.q))

        if request.fill and request.filters.begin_range:
            summary.fill(request.filters.begin_range)

        return GetGgoSummaryResponse(
            success=True,
            labels=summary.labels,
            groups=summary.groups,
        )


class GetTotalAmount(Controller):
    """
    TODO
    """
    Request = md.class_schema(GetTotalAmountRequest)
    Response = md.class_schema(GetTotalAmountResponse)

    @require_oauth('ggo.read')
    @inject_user
    @inject_session
    def handle_request(self, request, user, session):
        """
        :param GetTotalAmountRequest request:
        :param User user:
        :param sqlalchemy.orm.Session session:
        :rtype: GetTotalAmountResponse
        """
        query = GgoQuery(session) \
            .belongs_to(user) \
            .apply_filters(request.filters)

        return GetTotalAmountResponse(
            success=True,
            amount=query.get_total_amount(),
        )


class GetTransferSummary(Controller):
    """
    This endpoint works the same way as /ggo-summary, except it only
    summarized transferred GGOs, either inbound or outbound
    depending on the parameter "direction".
    """
    Request = md.class_schema(GetTransferSummaryRequest)
    Response = md.class_schema(GetTransferSummaryResponse)

    @require_oauth('ggo.transfer')
    @inject_user
    @inject_session
    def handle_request(self, request, user, session):
        """
        :param GetTransferSummaryRequest request:
        :param User user:
        :param sqlalchemy.orm.Session session:
        :rtype: GetTransferSummaryResponse
        """
        query = TransactionQuery(session) \
            .apply_filters(request.filters)

        if request.direction == TransferDirection.INBOUND:
            query = query.received_by_user(user)
        elif request.direction == TransferDirection.OUTBOUND:
            query = query.sent_by_user(user)
        else:
            query = query.sent_or_received_by_user(user)

        summary = query.get_summary(request.resolution, request.grouping)

        if request.fill and request.filters.begin_range:
            summary.fill(request.filters.begin_range)

        return GetTransferSummaryResponse(
            success=True,
            labels=summary.labels,
            groups=summary.groups,
        )


class GetTransferredAmount(Controller):
    """
    Summarizes the amount of transferred GGOs and returns the total amount
    of Wh as an integer. Takes the "filters" and "direction"
    like /transfers/summary.
    """
    Request = md.class_schema(GetTransferredAmountRequest)
    Response = md.class_schema(GetTransferredAmountResponse)

    @require_oauth('ggo.transfer')
    @inject_user
    @inject_session
    def handle_request(self, request, user, session):
        """
        :param GetTransferredAmountRequest request:
        :param User user:
        :param sqlalchemy.orm.Session session:
        :rtype: GetTransferredAmountResponse
        """
        query = TransactionQuery(session) \
            .apply_filters(request.filters)

        if request.direction == TransferDirection.INBOUND:
            query = query.received_by_user(user)
        elif request.direction == TransferDirection.OUTBOUND:
            query = query.sent_by_user(user)
        else:
            query = query.sent_or_received_by_user(user)

        return GetTransferredAmountResponse(
            success=True,
            amount=query.get_total_amount(),
        )


class ComposeGgo(Controller):
    """
    Provided an address to a [parent] GGO, this endpoint will split it up
    into multiple new GGOs ("composing" them from the parent) and transfer
    the new GGOs (children) to other accounts and/or retire them to any
    of the user's own MeteringPoints.

    To do this, provide one or more TransferRequests along with one or
    more RetireRequests.The sum of these can not exceed the parent GGO's
    amount, but can, however deceed it. Any remaining amount is automatically
    transferred back to the owner of the parent GGO.

    # Transfers

    Each TransferRequests contains an amount in Wh, an account ID to
    transfer the given amount to, and an arbitrary reference string
    for future enquiry if necessary.

    # Retires

    Each RetireRequests contains an amount in Wh, and a GSRN number to
    retire the specified amount to. The MeteringPoint, identified by the
    GSRN number, must belong to the user itself.

    # Concurrency

    The requested transfers and retires are considered successful upon
    response from this endpoint if the returned value of "success" is true.
    This means that subsequent requests to other endpoints will immediately
    assume the transfers or retires valid.

    However, due to the asynchronous nature of the blockchain ledger, this
    operation may be rolled back later for reasons that could not be foreseen
    at the time invoking this endpoint. This will result in the parent GGO
    being stored and available to the user's account again, thus also cancelling
    transfers and retires.
    """
    Request = md.class_schema(ComposeGgoRequest)
    Response = md.class_schema(ComposeGgoResponse)

    @require_oauth(['ggo.transfer', 'ggo.retire'])
    @inject_user
    @inject_session
    def handle_request(self, request, user, session):
        """
        :param ComposeGgoRequest request:
        :param User user:
        :param sqlalchemy.orm.Session session:
        :rtype: ComposeGgoResponse
        """
        batch, recipients = self.compose(
            user=user,
            ggo_address=request.address,
            transfers=request.transfers,
            retires=request.retires,
        )

        start_handle_composed_ggo_pipeline(batch, recipients, session)

        return ComposeGgoResponse(success=True)

    @atomic
    def compose(self, user, ggo_address, transfers, retires, session):
        """
        :param User user:
        :param str ggo_address:
        :param list[TransferRequest] transfers:
        :param list[RetireRequest] retires:
        :param sqlalchemy.orm.Session session:
        :rtype: (Batch, list[User])
        :returns: Tuple the composed Batch along with a list of users
            who receive GGO by transfers
        """
        ggo = self.get_ggo(user, ggo_address, session)
        composer = self.get_composer(ggo, session)

        for transfer in transfers:
            self.add_transfer(composer, transfer, session)

        for retire in retires:
            self.add_retire(user, composer, retire, session)

        try:
            batch, recipients = composer.build_batch()
        except composer.Empty:
            raise BadRequest('Nothing to transfer/retire')
        except composer.AmountUnavailable:
            raise BadRequest('Requested amount exceeds available amount')

        session.add(batch)

        return batch, recipients

    def add_transfer(self, composer, request, session):
        """
        :param GgoComposer composer:
        :param TransferRequest request:
        :param sqlalchemy.orm.Session session:
        """
        target_user = self.get_user(request.account, session)

        if target_user is None:
            raise BadRequest(f'Account unavailable ({request.account})')

        composer.add_transfer(target_user, request.amount, request.reference)

    def add_retire(self, user, composer, request, session):
        """
        :param User user:
        :param GgoComposer composer:
        :param RetireRequest request:
        :param sqlalchemy.orm.Session session:
        """
        meteringpoint = self.get_metering_point(user, request.gsrn, session)

        if meteringpoint is None:
            raise BadRequest(f'MeteringPoint unavailable (GSRN: {request.gsrn})')

        try:
            composer.add_retire(meteringpoint, request.amount)
        except composer.RetireMeasurementUnavailable as e:
            raise BadRequest((
                f'No measurement available at {e.begin} '
                f'for GSRN {e.gsrn}'
            ))
        except composer.RetireMeasurementInvalid as e:
            raise BadRequest(f'Can not retire GGO to measurement {e.measurement.address}')
        except composer.RetireAmountInvalid as e:
            raise BadRequest((
                f'Can only retire up to {e.allowed_amount} '
                f'(you tried to retire {e.amount})'
            ))

    def get_ggo(self, user, ggo_address, session):
        """
        :param User user:
        :param str ggo_address:
        :param sqlalchemy.orm.Session session:
        :rtype: Ggo
        """
        ggo = GgoQuery(session) \
            .belongs_to(user) \
            .has_address(ggo_address) \
            .is_tradable() \
            .one_or_none()

        if not ggo:
            raise BadRequest('GGO not found or is unavailable: %s' % ggo_address)

        return ggo

    def get_user(self, sub, session):
        """
        :param str sub:
        :param sqlalchemy.orm.Session session:
        :rtype: User
        """
        return UserQuery(session) \
            .has_sub(sub) \
            .one_or_none()

    def get_metering_point(self, user, gsrn, session):
        """
        :param User user:
        :param str gsrn:
        :param sqlalchemy.orm.Session session:
        :rtype: MeteringPoint
        """
        return MeteringPointQuery(session) \
            .belongs_to(user) \
            .has_gsrn(gsrn) \
            .is_consumption() \
            .one_or_none()

    def get_composer(self, *args, **kwargs):
        """
        :rtype: GgoComposer
        """
        return GgoComposer(*args, **kwargs)


class OnGgoIssuedWebhook(Controller):
    """
    Invoked by DataHubService when new GGO(s) have been issued
    to a specific meteringpoint.
    """
    Request = md.class_schema(OnGgosIssuedWebhookRequest)

    @validate_hmac
    @inject_session
    def handle_request(self, request, session):
        """
        :param OnGgosIssuedWebhookRequest request:
        :param sqlalchemy.orm.Session session:
        :rtype: bool
        """
        user = self.get_user(request.sub, session)

        if user and not self.ggo_exists(request.ggo.address, session):
            ggo = self.create_ggo(user, request.ggo)

            start_invoke_on_ggo_received_tasks(
                subject=request.sub,
                ggo_id=ggo.id,
                session=session,
            )

            return True

        return False

    @atomic
    def create_ggo(self, user, imported_ggo, session):
        """
        :param User user:
        :param origin.services.datahub.Ggo imported_ggo:
        :param sqlalchemy.orm.Session session:
        :rtype: Ggo
        """
        ggo = self.map_imported_ggo(user, imported_ggo)
        session.add(ggo)
        session.flush()
        return ggo

    def map_imported_ggo(self, user, imported_ggo):
        """
        :param User user:
        :param origin.services.datahub.Ggo imported_ggo:
        :rtype: Ggo
        """
        return Ggo(
            user_id=user.id,
            address=imported_ggo.address,
            issue_time=imported_ggo.issue_time,
            expire_time=imported_ggo.expire_time,
            begin=imported_ggo.begin,
            end=imported_ggo.end,
            amount=imported_ggo.amount,
            sector=imported_ggo.sector,
            technology_code=imported_ggo.technology_code,
            fuel_code=imported_ggo.fuel_code,
            synchronized=True,
            issued=True,
            stored=True,
            locked=False,
            issue_gsrn=imported_ggo.gsrn,
        )

    def get_user(self, sub, session):
        """
        :param str sub:
        :param sqlalchemy.orm.Session session:
        :rtype: User
        """
        return UserQuery(session) \
            .has_sub(sub) \
            .one_or_none()

    def ggo_exists(self, address, session):
        """
        :param str address:
        :param sqlalchemy.orm.Session session:
        """
        count = GgoQuery(session) \
            .has_address(address) \
            .count()

        return count > 0
