"""
Asynchronous tasks for submitting a composed GGO to the ledger.
Invokes the "GGO RECEIVED" webhook on completion.

One entrypoint exists:

    start_handle_composed_ggo_pipeline()

"""
from celery import group
from sqlalchemy import orm

from origin import logger
from origin.db import inject_session
from origin.tasks import celery_app
from origin.auth import User
from origin.ledger import Batch
from origin.ggo import Ggo, GgoQuery
from origin.settings import BATCH_RESUBMIT_AFTER_HOURS
from origin.webhooks import (
    WebhookEvent,
    WebhookService,
    WebhookError,
    WebhookConnectionError,
)

from .submit_batch_to_ledger import start_submit_batch_pipeline


# Settings
POLL_RETRY_DELAY = 10
POLL_MAX_RETRIES = (BATCH_RESUBMIT_AFTER_HOURS * 60 * 60) / POLL_RETRY_DELAY


# Services
webhook = WebhookService()


@inject_session
def start_handle_composed_ggo_pipeline(batch, recipients, session):
    """
    :param Batch batch:
    :param collections.abc.Iterable[(User, Ggo)] recipients:
    :param sqlalchemy.orm.Session session:
    """
    on_success_tasks = []

    # On success, invoke a webhook GgoReceived for each recipient
    # of a new GGO
    for user, ggo in recipients:
        subscriptions = webhook.get_subscriptions(
            event=WebhookEvent.ON_GGO_RECEIVED,
            subject=user.sub,
            session=session,
        )

        for subscription in subscriptions:
            on_success_tasks.append(invoke_webhook.si(
                subject=user.sub,
                ggo_id=ggo.id,
                batch_id=batch.id,
                subscription_id=subscription.id,
            ))

    # on_success =
    #
    # on_success = group(
    #     invoke_webhook.si(subject=user.sub, ggo_id=ggo.id, batch_id=batch.id)
    #     for user, ggo in recipients
    # )

    start_submit_batch_pipeline(
        subject=batch.user.sub,
        batch=batch,
        success=group(on_success_tasks) if on_success_tasks else None,
    )


@celery_app.task(
    bind=True,
    name='compose.invoke_webhook',
    default_retry_delay=POLL_RETRY_DELAY,
    max_retries=POLL_MAX_RETRIES,
)
@logger.wrap_task(
    title='Invoking webhook ON_GGO_RECEIVED (subscription ID: %(subscription_id)d)',
    pipeline='handle_composed_ggo_request',
    task='invoke_webhook',
)
@inject_session
def invoke_webhook(task, subject, ggo_id, batch_id, subscription_id, session):
    """
    :param celery.Task task:
    :param str subject:
    :param int ggo_id:
    :param int batch_id:
    :param int subscription_id:
    :param sqlalchemy.orm.Session session:
    """
    __log_extra = {
        'subject': subject,
        'ggo_id': str(ggo_id),
        'batch_id': str(batch_id),
        'subscription_id': str(subscription_id),
        'pipeline': 'compose',
        'task': 'invoke_webhook',
    }

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
