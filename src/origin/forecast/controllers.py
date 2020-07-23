from uuid import uuid4
import marshmallow_dataclass as md

from origin.http import Controller
from origin.db import inject_session, atomic
from origin.auth import UserQuery, inject_user, require_oauth
from origin.pipelines import start_invoke_on_forecast_received_tasks

from .queries import ForecastQuery
from .models import (
    Forecast,
    GetForecastRequest,
    GetForecastResponse,
    GetForecastListRequest,
    GetForecastListResponse,
    GetForecastSeriesResponse,
    SubmitForecastRequest,
    SubmitForecastResponse,
)


class GetForecast(Controller):
    """
    TODO
    """
    Request = md.class_schema(GetForecastRequest)
    Response = md.class_schema(GetForecastResponse)

    @require_oauth('ggo.read')
    @inject_user
    @inject_session
    def handle_request(self, request, user, session):
        """
        :param GetForecastRequest request:
        :param origin.auth.User user:
        :param sqlalchemy.orm.Session session:
        :rtype: GetForecastResponse
        """
        query = ForecastQuery(session) \
            .is_sent_or_received_by(user)

        if request.public_id:
            query = query.has_public_id(request.public_id)
        if request.reference:
            query = query.has_reference(request.reference)
        if request.at_time:
            query = query.at_time(request.at_time)

        forecast = query \
            .order_by(Forecast.created.desc()) \
            .first()

        return GetForecastResponse(
            success=forecast is not None,
            forecast=forecast,
        )


class GetForecastList(Controller):
    """
    TODO
    """
    Request = md.class_schema(GetForecastListRequest)
    Response = md.class_schema(GetForecastListResponse)

    @require_oauth('ggo.read')
    @inject_user
    @inject_session
    def handle_request(self, request, user, session):
        """
        :param GetForecastListRequest request:
        :param origin.auth.User user:
        :param sqlalchemy.orm.Session session:
        :rtype: GetForecastListResponse
        """
        query = ForecastQuery(session) \
            .is_sent_or_received_by(user)

        if request.reference:
            query = query.has_reference(request.reference)
        if request.at_time:
            query = query.at_time(request.at_time)

        total = query.count()

        query = query \
            .order_by(Forecast.created.desc()) \
            .offset(request.offset)

        if request.limit:
            query = query.limit(request.limit)

        return GetForecastListResponse(
            success=True,
            total=total,
            forecasts=query.all(),
        )


class GetForecastSeries(Controller):
    """
    TODO
    """
    Response = md.class_schema(GetForecastSeriesResponse)

    @require_oauth('ggo.read')
    @inject_user
    @inject_session
    def handle_request(self, user, session):
        """
        :param origin.auth.User user:
        :param sqlalchemy.orm.Session session:
        :rtype: GetGgoListResponse
        """
        sent = ForecastQuery(session) \
            .is_sent_by(user) \
            .get_distinct_references()

        received = ForecastQuery(session) \
            .is_received_by(user) \
            .get_distinct_references()

        return GetForecastSeriesResponse(
            success=True,
            sent=sent,
            received=received,
        )


class SubmitForecast(Controller):
    """
    TODO
    """
    Request = md.class_schema(SubmitForecastRequest)
    Response = md.class_schema(SubmitForecastResponse)

    @require_oauth('ggo.read')
    @inject_user
    def handle_request(self, request, user):
        """
        :param SubmitForecastRequest request:
        :param origin.auth.User user:
        :rtype: SubmitForecastResponse
        """
        forecast, recipient = self.create_forecast(request, user)

        self.invoke_webhooks(forecast, recipient)

        return SubmitForecastResponse(
            success=True,
            id=forecast.public_id,
        )

    @atomic
    def create_forecast(self, request, user, session):
        """
        :param SubmitForecastRequest request:
        :param origin.auth.User user:
        :param sqlalchemy.orm.Session session:
        :rtype: (Forecast, origin.auth.User)
        """
        recipient = UserQuery(session) \
            .has_sub(request.account) \
            .one()

        forecast = Forecast(
            public_id=uuid4(),
            user_id=user.id,
            recipient_id=recipient.id,
            begin=request.begin,
            end=request.begin + (request.resolution * len(request.forecast)),
            resolution=request.resolution.total_seconds(),
            sector=request.sector,
            reference=request.reference,
            forecast=request.forecast,
        )

        session.add(forecast)
        session.flush()

        return forecast, recipient

    @inject_session
    def invoke_webhooks(self, forecast, user, session):
        """
        :param Forecast forecast:
        :param origin.auth.User user:
        :param sqlalchemy.orm.Session session:
        """
        start_invoke_on_forecast_received_tasks(
            subject=user.sub,
            forecast_id=forecast.id,
            session=session,
        )
