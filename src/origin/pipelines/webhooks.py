from sqlalchemy import orm

from origin import logger
from origin.db import inject_session
from origin.tasks import celery_app
from origin.ggo import GgoQuery
from origin.settings import BATCH_RESUBMIT_AFTER_HOURS
from origin.webhooks import (
    WebhookEvent,
    WebhookService,
    WebhookError,
    WebhookConnectionError,
)


# Settings
RETRY_DELAY = 10
MAX_RETRIES = (24 * 60 * 60) / RETRY_DELAY


# Services
webhook = WebhookService()


def build_invoke_on_ggo_received_tasks(subject, ggo_id, session, **logging_kwargs):
    """
    :param str subject:
    :param int ggo_id:
    :param sqlalchemy.orm.Session session:
    :rtype: list[celery.Task]
    """
    tasks = []

    subscriptions = webhook.get_subscriptions(
        event=WebhookEvent.ON_GGO_RECEIVED,
        subject=subject,
        session=session,
    )

    for subscription in subscriptions:
        tasks.append(invoke_on_ggo_received.si(
            subject=subject,
            ggo_id=ggo_id,
            subscription_id=subscription.id,
            **logging_kwargs,
        ))

    return tasks


@celery_app.task(
    bind=True,
    name='webhooks.invoke_on_ggo_received',
    default_retry_delay=RETRY_DELAY,
    max_retries=MAX_RETRIES,
)
@logger.wrap_task(
    title='Invoking webhook ON_GGO_RECEIVED',
    pipeline='webhooks',
    task='invoke_on_ggo_received',
)
@inject_session
def invoke_on_ggo_received(task, subject, ggo_id, subscription_id, session, **logging_kwargs):
    """
    :param celery.Task task:
    :param str subject:
    :param int ggo_id:
    :param int subscription_id:
    :param sqlalchemy.orm.Session session:
    """
    __log_extra = logging_kwargs.copy()
    __log_extra.update({
        'subject': subject,
        'ggo_id': str(ggo_id),
        'subscription_id': str(subscription_id),
        'pipeline': 'webhooks',
        'task': 'invoke_on_ggo_received',
    })

    # Get GGO from database
    try:
        ggo = GgoQuery(session) \
            .has_id(ggo_id) \
            .one()
    except orm.exc.NoResultFound:
        raise
    except Exception as e:
        logger.exception('Failed to load Ggo from database', extra=__log_extra)
        raise task.retry(exc=e)

    # Get webhook subscription from database
    try:
        subscription = webhook.get_subscription(subscription_id, session)
    except orm.exc.NoResultFound:
        raise
    except Exception as e:
        logger.exception('Failed to load WebhookSubscription from database', extra=__log_extra)
        raise task.retry(exc=e)

    # Publish event to webhook
    try:
        webhook.on_ggo_received(subscription, ggo)
    except WebhookConnectionError as e:
        logger.exception('Failed to invoke webhook: ON_GGO_RECEIVED (Connection error)', extra=__log_extra)
        raise task.retry(exc=e)
    except WebhookError as e:
        logger.exception('Failed to invoke webhook: ON_GGO_RECEIVED', extra=__log_extra)
        raise task.retry(exc=e)
