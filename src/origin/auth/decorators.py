from authlib.integrations.flask_oauth2 import (
    ResourceProtector,
    current_token,
)

from origin.db import inject_session
from origin.http import Unauthorized

from .models import User
from .queries import UserQuery
from .token import TokenValidator


require_oauth = ResourceProtector()
require_oauth.register_token_validator(TokenValidator())


def inject_token(func):
    """
    Function decorator which injects a named parameter "token".

    The value is the authentication token provided by the
    client in a HTTP header.
    """
    def inject_token_wrapper(*args, **kwargs):
        kwargs['token'] = current_token
        return func(*args, **kwargs)
    return inject_token_wrapper


def inject_user(func):
    """
    Function decorator which injects a named parameter "user".

    The value is a User object.
    """
    def inject_user_wrapper(*args, **kwargs):
        user = _get_user()
        if not user:
            raise Unauthorized()
        kwargs['user'] = user
        return func(*args, **kwargs)
    return inject_user_wrapper


@inject_session
def _get_user(session):
    """
    :param Session session:
    :rtype: User
    """
    return UserQuery(session) \
        .has_sub(current_token.subject) \
        .one_or_none()
