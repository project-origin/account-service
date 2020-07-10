import json
import requests
import marshmallow
import marshmallow_dataclass as md

from origin.settings import ENERGY_TYPE_SERVICE_URL, DEBUG

from .models import GetMixEmissionsResponse


class EnergyTypeServiceConnectionError(Exception):
    """
    Raised when invoking EnergyTypeService results
    in a connection error
    """
    pass


class EnergyTypeServiceError(Exception):
    """
    Raised when invoking EnergyTypeService results
    in a status code != 200
    """
    def __init__(self, message, status_code=None, response_body=None):
        super(EnergyTypeServiceError, self).__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class EnergyTypeUnavailable(Exception):
    """
    Raised when requesting energy type which is unavailable
    for the requested GSRN
    """
    pass


class EnergyTypeService(object):
    """
    Interface for importing data from EnergyTypeService.
    """
    def invoke(self, path, query, response_schema):
        """
        :param str path:
        :param Schema response_schema:
        :rtype obj:
        """
        url = '%s%s' % (ENERGY_TYPE_SERVICE_URL, path)
        headers = {
            'Content-type': 'application/json',
            'accept': 'application/json',
        }

        try:
            response = requests.get(
                url=url,
                params=query,
                verify=not DEBUG,
                headers=headers,
            )
        except:
            raise EnergyTypeServiceConnectionError(
                'Failed request to EnergyTypeService')

        if response.status_code != 200:
            raise EnergyTypeServiceError(
                (
                    f'Invoking EnergyTypeService resulted in status code {response.status_code}: '
                    f'{url}\n\n{response.content}'
                ),
                status_code=response.status_code,
                response_body=str(response.content),
            )

        try:
            response_json = response.json()
            response_model = response_schema().load(response_json)
        except json.decoder.JSONDecodeError:
            raise EnergyTypeServiceError(
                f'Failed to parse response JSON: {url}\n\n{response.content}',
                status_code=response.status_code,
                response_body=str(response.content),
            )
        except marshmallow.ValidationError as e:
            raise EnergyTypeServiceError(
                f'Failed to validate response JSON: {url}\n\n{response.content}\n\n{str(e)}',
                status_code=response.status_code,
                response_body=str(response.content),
            )

        return response_model

    def get_residual_mix(self, sector, begin_from, begin_to):
        """
        Returns a dict of emission data for a MeteringPoint.

        :param list[str] sector:
        :param datetime.datetime begin_from:
        :param datetime.datetime begin_to:
        :rtype: GetMixEmissionsResponse
        """
        return self.invoke(
            path='/residual-mix',
            response_schema=md.class_schema(GetMixEmissionsResponse),
            query={
                'sector': sector,
                'begin_from': begin_from.isoformat(),
                'begin_to': begin_to.isoformat(),
            },
        )
