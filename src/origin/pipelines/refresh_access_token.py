"""
Asynchronous tasks for refreshing access tokens which
are close to expiring.
"""
from sqlalchemy import orm
from celery import group, shared_task
from datetime import datetime, timezone

from origin import logger
from origin.db import inject_session, atomic
from origin.auth import UserQuery, AuthBackend


# Settings
RETRY_DELAY = 10
MAX_RETRIES = (60 * 15) / RETRY_DELAY


# Services
backend = AuthBackend()


def start_refresh_expiring_tokens_pipeline():
    """
    Starts a pipeline which refreshes all tokens that are
    soon to expire.

    :rtype: celery.Task
    """
    return get_soon_to_expire_tokens \
        .s() \
        .apply_async()


def start_refresh_token_for_subject_pipeline(subject):
    """
    Starts a pipeline which refreshes token for a specific subject.

    :rtype: celery.Task
    """
    return refresh_token \
        .s(subject=subject) \
        .apply_async()


@shared_task(
    name='refresh_token.get_soon_to_expire_tokens',
    autoretry_for=(Exception,),
    default_retry_delay=RETRY_DELAY,
    max_retries=MAX_RETRIES,
)
@logger.wrap_task(
    title='Getting soon-to-expire tokens',
    pipeline='refresh_token',
    task='get_soon_to_expire_tokens',
)
@inject_session
def get_soon_to_expire_tokens(session):
    """
    :param sqlalchemy.orm.Session session:
    """
    users = UserQuery(session) \
        .is_active() \
        .should_refresh_token()

    tasks = [refresh_token.si(subject=user.sub) for user in users]

    group(*tasks).apply_async()


@shared_task(
    name='refresh_token.refresh_token_for_user',
    autoretry_for=(Exception,),
    default_retry_delay=RETRY_DELAY,
    max_retries=MAX_RETRIES,
)
@logger.wrap_task(
    title='Refreshing user\'s access token',
    pipeline='refresh_token',
    task='refresh_token',
)
@atomic
def refresh_token(subject, session):
    """
    :param str subject:
    :param sqlalchemy.orm.Session session:
    """
    __log_extra = {
        'subject': subject,
        'pipeline': 'refresh_token',
        'task': 'refresh_token',
    }

    try:
        user = UserQuery(session) \
            .is_active() \
            .has_sub(subject) \
            .one()
    except orm.exc.NoResultFound:
        logger.info('Could not refresh token: User not found', extra=__log_extra)
        return
    except Exception as e:
        raise

    token = backend.refresh_token(user.refresh_token)

    user.access_token = token['access_token']
    user.refresh_token = token['refresh_token']
    user.token_expire = datetime \
        .fromtimestamp(token['expires_at']) \
        .replace(tzinfo=timezone.utc)
