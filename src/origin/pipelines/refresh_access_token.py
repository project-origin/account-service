"""
TODO write this
"""
import logging
from datetime import datetime, timezone
from celery import group

from origin.db import inject_session, atomic
from origin.auth import UserQuery, AuthBackend
from origin.tasks import celery_app


backend = AuthBackend()


@celery_app.task(
    name='refresh_token.get_soon_to_expire_tokens',
    max_retries=None,
)
@inject_session
def get_soon_to_expire_tokens(session):
    """
    :param Session session:
    """
    logging.info('--- get_soon_to_expire_tokens')

    users = UserQuery(session) \
        .should_refresh_token()

    tasks = [refresh_token.si(user.id) for user in users]

    group(*tasks).apply_async()


@celery_app.task(
    name='refresh_token.refresh_token_for_user',
    max_retries=None,
)
@atomic
def refresh_token(user_id, session):
    """
    :param int user_id:
    :param Session session:
    """
    logging.info(f'--- refresh_token_for_user, user_id={user_id}')

    user = UserQuery(session) \
        .has_id(user_id) \
        .one()

    token = backend.refresh_token(user.refresh_token)

    user.access_token = token['access_token']
    user.refresh_token = token['refresh_token']
    user.token_expire = datetime \
        .fromtimestamp(token['expires_at']) \
        .replace(tzinfo=timezone.utc)
