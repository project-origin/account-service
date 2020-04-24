import requests
import marshmallow_dataclass as md

from origin.settings import (
    PROJECT_URL,
    DATAHUB_SERVICE_URL,
    TOKEN_HEADER,
)

from .models import (
    GetGgoListRequest,
    GetGgoListResponse,
    GetMeasurementRequest,
    GetMeasurementResponse,
    GetMeasurementSummaryRequest,
    GetMeasurementSummaryResponse,
    GetMeteringPointsResponse,
    SetKeyRequest,
    SetKeyResponse,
    WebhookSubscribeRequest,
    WebhookSubscribeResponse,
)


class DataHubService(object):
    """
    An interface to the Project Origin DataHub Service API.
    """
    def invoke(self, token, path, response_schema, request=None, request_schema=None):
        """
        :param str token:
        :param str path:
        :param obj request:
        :param Schema request_schema:
        :param Schema response_schema:
        :rtype obj:
        """
        if request and request_schema:
            body = request_schema().dump(request)
        else:
            body = None

        response = requests.post(
            url='%s%s' % (DATAHUB_SERVICE_URL, path),
            json=body,
            headers={TOKEN_HEADER: f'Bearer {token}'},
        )

        if response.status_code != 200:
            raise Exception('%s\n\n%s\n\n%s\n\n%s\n\n' % (str(response), path, body, response.content))

        response_json = response.json()

        return response_schema().load(response_json)

    def set_key(self, token, gsrn, key):
        """
        :param str token:
        :param str gsrn:
        :param str key:
        :rtype: SetKeyResponse
        """
        return self.invoke(
            token=token,
            path='/meteringpoints/set-key',
            request=SetKeyRequest(gsrn=gsrn, key=key),
            request_schema=md.class_schema(SetKeyRequest),
            response_schema=md.class_schema(SetKeyResponse),
        )

    def get_meteringpoints(self, token):
        """
        :param str token:
        :rtype: GetMeteringPointsResponse
        """
        return self.invoke(
            token=token,
            path='/meteringpoints',
            response_schema=md.class_schema(GetMeteringPointsResponse),
        )

    def get_ggo_list(self, token, request):
        """
        :param str token:
        :param GetGgoListRequest request:
        :rtype: GetGgoListResponse
        """
        return self.invoke(
            token=token,
            path='/ggo',
            request=request,
            request_schema=md.class_schema(GetGgoListRequest),
            response_schema=md.class_schema(GetGgoListResponse),
        )

    # def get_measurement_summary(self, token, request):
    #     """
    #     :param str token:
    #     :param GetMeasurementSummaryRequest request:
    #     :rtype: GetMeasurementSummaryResponse
    #     """
    #     return self.invoke(
    #         token=token,
    #         path='/measurements/summary',
    #         request=request,
    #         request_schema=md.class_schema(GetMeasurementSummaryRequest),
    #         response_schema=md.class_schema(GetMeasurementSummaryResponse),
    #     )
    #
    # def get_production(self, token, request):
    #     """
    #     :param str token:
    #     :param GetMeasurementRequest request:
    #     :rtype: GetMeasurementResponse
    #     """
    #     return self.invoke(
    #         token=token,
    #         path='/measurements/produced',
    #         request=request,
    #         request_schema=md.class_schema(GetMeasurementRequest),
    #         response_schema=md.class_schema(GetMeasurementResponse),
    #     )

    def get_consumption(self, token, request):
        """
        :param str token:
        :param GetMeasurementRequest request:
        :rtype: GetMeasurementResponse
        """
        return self.invoke(
            token=token,
            path='/measurements/consumed',
            request=request,
            request_schema=md.class_schema(GetMeasurementRequest),
            response_schema=md.class_schema(GetMeasurementResponse),
        )

    def webhook_on_meteringpoints_available_subscribe(self, token):
        """
        :param str token:
        :rtype: WebhookSubscribeResponse
        """
        url = f'{PROJECT_URL}/webhook/on-meteringpoints-available'

        return self.invoke(
            token=token,
            path='/webhook/on-meteringpoints-available/subscribe',
            request=WebhookSubscribeRequest(url=url),
            request_schema=md.class_schema(WebhookSubscribeRequest),
            response_schema=md.class_schema(WebhookSubscribeResponse),
        )

    def webhook_on_ggos_issued_subscribe(self, token):
        """
        :param str token:
        :rtype: WebhookSubscribeResponse
        """
        url = f'{PROJECT_URL}/webhook/on-ggos-issued'

        return self.invoke(
            token=token,
            path='/webhook/on-ggos-issued/subscribe',
            request=WebhookSubscribeRequest(url=url),
            request_schema=md.class_schema(WebhookSubscribeRequest),
            response_schema=md.class_schema(WebhookSubscribeResponse),
        )
