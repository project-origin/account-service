import marshmallow_dataclass as md

from origin.db import inject_session, atomic
from origin.http import Controller, BadRequest
from origin.auth import User, inject_token, inject_user, require_oauth
from origin.pipelines import (
    start_handle_composed_ggo_pipeline,
    start_import_issued_ggos,
)

from .composer import GgoComposer, GgoComposition
from .queries import GgoQuery, TransactionQuery, RetireQuery
from .models import (
    TransferDirection,
    TransferRequest,
    RetireRequest,
    GgoCategory,
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
    grouping: gsrn |  sector | technologyCode | fuelCode
    resolution: year | month | day | hour | all

    beginFrom: INCLUSIVE
    beginTo: EXCLUSIVE

    # TODO resolutionIso: https://www.digi.com/resources/documentation/digidocs/90001437-13/reference/r_iso_8601_duration_format.htm
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
        query = GgoQuery(session) \
            .belongs_to(user) \
            .apply_filters(request.filters)

        if request.category == GgoCategory.ISSUED:
            query = query.is_issued(True)
        elif request.category == GgoCategory.STORED:
            query = query.is_stored(True).is_expired(False)
        elif request.category == GgoCategory.RETIRED:
            query = query.is_retired(True)
        elif request.category == GgoCategory.EXPIRED:
            query = query.is_stored(True).is_expired(True)
        else:
            raise RuntimeError('Should NOT have happened!')

        summary = query.get_summary(request.resolution, request.grouping)

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
    @inject_token
    def handle_request(self, request, user, token):
        """
        :param ComposeGgoRequest request:
        :param User user:
        :param str token:
        :rtype: ComposeGgoResponse
        """
        composition = self.compose(
            user=user,
            token=token,
            ggo_address=request.address,
            transfers=request.transfers,
            retires=request.retires,
        )

        start_handle_composed_ggo_pipeline(
            batch=composition.batch,
            recipients=composition.recipients,
        )

        return ComposeGgoResponse(success=True)

    @atomic
    def compose(self, user, token, ggo_address,
                transfers, retires, session):
        """
        :param User user:
        :param str token:
        :param str ggo_address:
        :param list[TransferRequest] transfers:
        :param list[RetireRequest] retires:
        :param Session session:
        :rtype: GgoComposition
        """
        ggo = self.get_ggo(user, ggo_address, session)
        composer = self.get_composer(ggo, token, session)

        try:
            composer.add_many_transfers(transfers)
            composer.add_many_retires(retires)
            composition = composer.compose()
        except GgoComposer.AmountUnavailable:
            raise BadRequest('Requested amount exceeds available amount')
        except GgoComposer.RetireGSRNInvalid as e:
            raise BadRequest('Can not retire GGO to GSRN %s' % e.gsrn)
        except GgoComposer.RetireMeasurementInvalid as e:
            raise BadRequest('Can not retire GGO to measurement %s'
                             % e.measurement.address)

        session.add(composition.batch)

        return composition

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

    def get_composer(self, ggo, token, session):
        """
        :param str token:
        :param Ggo ggo:
        :param Session session:
        :rtype: GgoComposer
        """
        return GgoComposer(ggo, token, session)


class OnGgosIssuedWebhook(Controller):
    """
    TODO
    """
    Request = md.class_schema(OnGgosIssuedWebhookRequest)

    def handle_request(self, request):
        """
        :param OnGgosIssuedWebhookRequest request:
        :rtype: bool
        """
        start_import_issued_ggos(request)

        return True
