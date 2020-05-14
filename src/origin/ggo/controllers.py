import marshmallow_dataclass as md

from origin.db import inject_session, atomic
from origin.http import Controller, BadRequest
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
from origin.webhooks import validate_hmac

from .composer import GgoComposer
from .queries import GgoQuery, TransactionQuery, RetireQuery
from .models import (
    TransferDirection,
    TransferRequest,
    RetireRequest,
    GetGgoListRequest,
    GetGgoListResponse,
    GetGgoSummaryRequest,
    GetGgoSummaryResponse,
    GetTransferSummaryRequest,
    GetTransferSummaryResponse,
    GetTransferredAmountRequest,
    GetTransferredAmountResponse,
    ComposeGgoRequest,
    ComposeGgoResponse,
    GetRetiredAmountResponse,
    GetRetiredAmountRequest,
    OnGgosIssuedWebhookRequest,
    Ggo,
)


class GetGgoList(Controller):
    """
    order: period | amount | sector | gsrn  # TODO asc/desc?

    beginFrom: INCLUSIVE
    beginTo: EXCLUSIVE
    """
    Request = md.class_schema(GetGgoListRequest)
    Response = md.class_schema(GetGgoListResponse)

    @require_oauth('ggo.read')
    @inject_user(required=True)
    @inject_session
    def handle_request(self, request, user, session):
        """
        :param GetGgoListRequest request:
        :param User user:
        :param Session session:
        :rtype: GetGgoListResponse
        """
        query = GgoQuery(session) \
            .belongs_to(user) \
            .apply_filters(request.filters)

        results = query \
            .order_by(Ggo.begin) \
            .offset(request.offset) \
            .limit(request.limit) \
            .all()

        total = query.count()

        return GetGgoListResponse(
            success=True,
            total=total,
            results=results,
        )


class GetGgoSummary(Controller):
    """
    TODO
    TODO resolutionIso: https://www.digi.com/resources/documentation/digidocs/90001437-13/reference/r_iso_8601_duration_format.htm
    """
    Request = md.class_schema(GetGgoSummaryRequest)
    Response = md.class_schema(GetGgoSummaryResponse)

    @require_oauth('ggo.read')
    @inject_user(required=True)
    @inject_session
    def handle_request(self, request, user, session):
        """
        :param GetGgoSummaryRequest request:
        :param User user:
        :param Session session:
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


class GetTransferSummary(Controller):
    """
    TODO
    """
    Request = md.class_schema(GetTransferSummaryRequest)
    Response = md.class_schema(GetTransferSummaryResponse)

    @require_oauth('ggo.transfer')
    @inject_user(required=True)
    @inject_session
    def handle_request(self, request, user, session):
        """
        :param GetTransferSummaryRequest request:
        :param User user:
        :param Session session:
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
    TODO
    """
    Request = md.class_schema(GetTransferredAmountRequest)
    Response = md.class_schema(GetTransferredAmountResponse)

    @require_oauth('ggo.transfer')
    @inject_user(required=True)
    @inject_session
    def handle_request(self, request, user, session):
        """
        :param GetTransferredAmountRequest request:
        :param User user:
        :param Session session:
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
    TODO
    """
    Request = md.class_schema(GetRetiredAmountRequest)
    Response = md.class_schema(GetRetiredAmountResponse)

    @require_oauth('ggo.retire')
    @inject_user(required=True)
    @inject_session
    def handle_request(self, request, user, session):
        """
        :param GetRetiredAmountRequest request:
        :param User user:
        :param Session session:
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


class TransferGgo(Controller):
    """
    TODO
    """
    # Request = md.class_schema(TransferGgoRequest)
    # Response = md.class_schema(TransferGgoResponse)

    # builder = BatchBuilder()

    @require_oauth('ggo.transfer')
    @inject_user(required=True)
    def handle_request(self, request, user):
        """
        :param TransferGgoRequest request:
        :param User user:
        :rtype: TransferGgoResponse
        """
    #     claim = self.build_claim(request, user)
    #
    #     start_submit_transfer_claim_pipeline(claim)
    #
    #     return TransferGgoResponse(success=True)
    #
    # @atomic
    # def build_claim(self, request, user, session):
    #     """
    #     :param TransferGgoRequest request:
    #     :param User user:
    #     :param Session session:
    #     :rtype: TransferClaim
    #     """
    #     user = session.merge(user)
    #
    #     user_to = UserQuery(session) \
    #         .has_account_number(request.account_number) \
    #         .one()
    #
    #     claim = TransferClaim.from_request(
    #         user_from=user,
    #         user_to=user_to,
    #         request=request,
    #     )
    #
    #     claim.batch = self.builder.build_batch(claim, session)
    #
    #     session.add(claim)
    #     session.flush()
    #
    #     return claim


class ComposeGgo(Controller):
    """
    TODO
    """
    Request = md.class_schema(ComposeGgoRequest)
    Response = md.class_schema(ComposeGgoResponse)

    @require_oauth(['ggo.transfer', 'ggo.retire'])
    @inject_user(required=True)
    def handle_request(self, request, user):
        """
        :param ComposeGgoRequest request:
        :param User user:
        :rtype: ComposeGgoResponse
        """
        batch, recipients = self.compose(
            user=user,
            ggo_address=request.address,
            transfers=request.transfers,
            retires=request.retires,
        )

        start_handle_composed_ggo_pipeline(batch, recipients)

        return ComposeGgoResponse(success=True)

    @atomic
    def compose(self, user, ggo_address, transfers, retires, session):
        """
        :param User user:
        :param str ggo_address:
        :param list[TransferRequest] transfers:
        :param list[RetireRequest] retires:
        :param Session session:
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
        :param Session session:
        """
        target_user = self.get_user(request.sub, session)

        if target_user is None:
            raise BadRequest(f'Account unavailable ({request.sub})')

        composer.add_transfer(target_user, request.amount, request.reference)

    def add_retire(self, user, composer, request, session):
        """
        :param User user:
        :param GgoComposer composer:
        :param RetireRequest request:
        :param Session session:
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
        :param Session session:
        :rtype: Ggo
        """
        ggo = GgoQuery(session) \
            .belongs_to(user) \
            .has_address(ggo_address) \
            .is_tradable() \
            .one_or_none()

        if not ggo:
            raise BadRequest('GGO not found or is unavailable')

        return ggo

    def get_user(self, sub, session):
        """
        :param str sub:
        :param Session session:
        :rtype: User
        """
        return UserQuery(session) \
            .has_sub(sub) \
            .one_or_none()

    def get_metering_point(self, user, gsrn, session):
        """
        :param User user:
        :param str gsrn:
        :param Session session:
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
        start_import_issued_ggos(request)

        return True
