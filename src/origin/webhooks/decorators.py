import hmac
from base64 import b64encode
from flask import request
from hashlib import sha256

from origin.http import Unauthorized
from origin.settings import HMAC_HEADER, WEBHOOK_SECRET


def validate_hmac(func):

    def _validate_hmac(*args, **kwargs):

        header = request.headers.get(HMAC_HEADER)
        hmac = 'sha256=' + b64encode(hmac.new(WEBHOOK_SECRET.encode(), request.content, sha256).digest())

        if hmac != header:
            raise Unauthorized()
        
        return func(*args, **kwargs)

    return _validate_hmac
