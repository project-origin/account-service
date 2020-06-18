import marshmallow_dataclass as md

from origin.db import inject_session, atomic
from origin.http import Controller, BadRequest
from origin.webhooks import validate_hmac
from origin.pipelines import (
    start_handle_composed_ggo_pipeline,
    start_import_issued_ggos,
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
from .queries import GgoQuery, TransactionQuery, RetireQuery
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
    GetRetiredAmountResponse,
    GetRetiredAmountRequest,
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


class GetRetiredAmount(Controller):
    """
    Summarizes the amount of retired GGOs and returns the total
    amount of Wh as an integer.
    """
    Request = md.class_schema(GetRetiredAmountRequest)
    Response = md.class_schema(GetRetiredAmountResponse)

    @require_oauth('ggo.retire')
    @inject_user
    @inject_session
    def handle_request(self, request, user, session):
        """
        :param GetRetiredAmountRequest request:
        :param User user:
        :param sqlalchemy.orm.Session session:
        :rtype: GetRetiredAmountResponse
        """
        amount = RetireQuery(session) \
            .belongs_to(user) \
            .apply_filters(request.filters) \
            .get_total_amount()

        return GetRetiredAmountResponse(
            success=True,
            amount=amount,
        )


class ComposeGgo(Controller):
    """
    Transfers or retires a single GGO to one or more accounts and/or
    MeteringPoints. The operation splits the source GGO up into multiple
    new GGOs if required to before transferring and retiring takes place.

    The sum of these can not exceed the source GGO's amount, but can,
    however deceed it. Any remaining amount is transferred back to
    the owner of the source GGO.

    Each transfer request contains an amount in Wh, a reference string
    for future enquiry, and a subject (sub), which is the recipient user's
    account number.

    Each retire request contains an amount in Wh, and a GSRN number to
    retire the specified amount to.

    The requested transfers and retires are counted as complete upon a
    successful response from this endpoint. This means that subsequent
    requests to other endpoints will count the requested amount transferred
    or retired immediately. However, due to the asynchronous nature of
    the blockchain ledger, this operation may be rolled back later in
    case of an error on the ledger, and will result in the source GGO
    being stored and available to the source' account again.
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
        meteringpoint = self.get_metering_point(
            user, request.gsrn, session)

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
            .one_or_none()

    def get_composer(self, *args, **kwargs):
        """
        :rtype: GgoComposer
        """
        return GgoComposer(*args, **kwargs)


class OnGgosIssuedWebhook(Controller):
    """
    Invoked by DataHubService when new GGO(s) have been issued
    to a specific meteringpoint.
    """
    Request = md.class_schema(OnGgosIssuedWebhookRequest)

    @validate_hmac
    def handle_request(self, request):
        """
        :param OnGgosIssuedWebhookRequest request:
        :rtype: bool
        """
        start_import_issued_ggos(
            subject=request.sub,
            gsrn=request.gsrn,
            begin=request.begin,
        )

        return True
