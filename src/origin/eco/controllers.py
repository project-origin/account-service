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


class GetEcoDeclaration(Controller):
    """
    TODO
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