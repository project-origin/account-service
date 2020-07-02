import json
import requests
import marshmallow
import marshmallow_dataclass as md

from origin.settings import (
    PROJECT_URL,
    DATAHUB_SERVICE_URL,
    TOKEN_HEADER,
    DEBUG,
    WEBHOOK_SECRET,
)

from .models import (
    GetGgoListRequest,
    GetGgoListResponse,
    GetMeasurementRequest,
    GetMeasurementResponse,
    GetMeteringPointsResponse,
    SetKeyRequest,
    SetKeyResponse,
    WebhookSubscribeRequest,
    WebhookSubscribeResponse,
    GetTechnologiesResponse,
)


class DataHubServiceConnectionError(Exception):
    """
    Raised when invoking DataHubService results in a connection error
    """
    pass


class DataHubServiceError(Exception):
    """
    Raised when invoking DataHubService results in a status code != 200
    """
    def __init__(self, message, status_code, response_body):
        super(DataHubServiceError, self).__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class DataHubService(object):
    """
    An interface to the Project Origin DataHub Service API.
    """
    def invoke(self, path, response_schema, token=None, request=None, request_schema=None):
        """
        :param str path:
        :param obj request:
        :param str token:
        :param Schema request_schema:
        :param Schema response_schema:
        :rtype obj:
        """
        url = '%s%s' % (DATAHUB_SERVICE_URL, path)
        headers = {}
        body = None

        if token:
            headers = {TOKEN_HEADER: f'Bearer {token}'}
        if request and request_schema:
            body = request_schema().dump(request)

        try:
            response = requests.post(
                url=url,
                json=body,
                headers=headers,
                verify=not DEBUG,
            )
        except:
            raise DataHubServiceConnectionError(
                'Failed to POST request to DataHubService')

        if response.status_code != 200:
            raise DataHubServiceError(
                (
                    f'Invoking webhook resulted in status code {response.status_code}: '
                    f'{url}\n\n{response.content}'
                ),
                status_code=response.status_code,
                response_body=str(response.content),
            )

        try:
            response_json = response.json()
            response_model = response_schema().load(response_json)
        except json.decoder.JSONDecodeError:
            raise DataHubServiceError(
                f'Failed to parse response JSON: {url}\n\n{response.content}',
                status_code=response.status_code,
                response_body=str(response.content),
            )
        except marshmallow.ValidationError:
            raise DataHubServiceError(
                f'Failed to validate response JSON: {url}\n\n{response.content}',
                status_code=response.status_code,
                response_body=str(response.content),
            )

        return response_model

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

    def webhook_on_meteringpoint_available_subscribe(self, token):
        """
        :param str token:
        :rtype: WebhookSubscribeResponse
        """
        callback_url = f'{PROJECT_URL}/webhook/on-meteringpoints-available'

        return self.invoke(
            token=token,
            path='/webhook/on-meteringpoints-available/subscribe',
            request=WebhookSubscribeRequest(url=callback_url, secret=WEBHOOK_SECRET),
            request_schema=md.class_schema(WebhookSubscribeRequest),
            response_schema=md.class_schema(WebhookSubscribeResponse),
        )

    def webhook_on_ggo_issued_subscribe(self, token):
        """
        :param str token:
        :rtype: WebhookSubscribeResponse
        """
        callback_url = f'{PROJECT_URL}/webhook/on-ggo-issued'

        return self.invoke(
            token=token,
            path='/webhook/on-ggo-issued/subscribe',
            request=WebhookSubscribeRequest(url=callback_url, secret=WEBHOOK_SECRET),
            request_schema=md.class_schema(WebhookSubscribeRequest),
            response_schema=md.class_schema(WebhookSubscribeResponse),
        )

    def get_technologies(self):
        """
        :rtype: GetTechnologiesResponse
        """
        return self.invoke(
            path='/technologies',
            response_schema=md.class_schema(GetTechnologiesResponse),
        )
