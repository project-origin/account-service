import hmac
from base64 import b64encode
from flask import request
from hashlib import sha256

from origin.http import Unauthorized
from origin.settings import HMAC_HEADER, WEBHOOK_SECRET


def validate_hmac(func):
    """
    TODO
    """
    def _validate_hmac_wrapper(*args, **kwargs):
        hmac_header = request.headers.get(HMAC_HEADER)
        hmac_value = 'sha256=' + b64encode(hmac.new(
            WEBHOOK_SECRET.encode(),
            request.data,
            sha256
        ).digest()).decode()

        if hmac_value != hmac_header:
            raise Unauthorized()

        return func(*args, **kwargs)

    return _validate_hmac_wrapper
