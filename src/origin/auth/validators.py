"""
Additional common schema validators for JSON-to-model validation.
Plugs into Marshmallow's validation model and can be used in
conjunction with the marshmallow and marshmallow-dataclass libraries.
"""
from marshmallow import ValidationError

from origin.db import inject_session

from origin.auth.queries import UserQuery


@inject_session
def sub_exists(sub, session, *args, **kwargs):
    """
    Validates that a list of items are unique,
    ie. no value are present more than once.
    """
    user = UserQuery(session) \
        .has_sub(sub) \
        .one_or_none()

    if user is None:
        raise ValidationError('No user exists with subject: %s' % sub)
