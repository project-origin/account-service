"""
Asynchronous tasks for submitting a composed GGO to the ledger.
Invokes the "GGO RECEIVED" webhook on completion.

One entrypoint exists:

    start_handle_composed_ggo_pipeline()

"""
from celery import group

from origin import logger
from origin.db import inject_session
from origin.tasks import celery_app
from origin.webhooks import WebhookService
from origin.auth import User
from origin.ledger import Batch
from origin.ggo import Ggo, GgoQuery

from .submit_batch_to_ledger import start_submit_batch_pipeline


webhook = WebhookService()


def start_handle_composed_ggo_pipeline(batch, recipients):
    """
    :param Batch batch:
    :param collections.abc.Iterable[(User, Ggo)] recipients:
    """

    # On success, invoke a webhook GgoReceived for each recipient
    # of a new GGO
    on_success = group(
        invoke_webhook.si(subject=user.sub, ggo_id=ggo.id)
        for user, ggo in recipients
    )

    start_submit_batch_pipeline(
        subject=batch.user.sub,
        batch=batch,
        success=on_success,
    )


@celery_app.task(
    name='compose.invoke_webhook',
    autoretry_for=(Exception,),
    retry_backoff=2,
    max_retries=5,
)
@logger.wrap_task(
    title='Invoking webhook on_ggo_received',
    pipeline='handle_composed_ggo_request',
    task='invoke_webhook',
)
@inject_session
def invoke_webhook(subject, ggo_id, session):
    """
    :param str subject:
    :param int ggo_id:
    :param sqlalchemy.orm.Session session:
    """
    ggo = GgoQuery(session) \
        .has_id(ggo_id) \
        .one()

    webhook.on_ggo_received(subject, ggo)
