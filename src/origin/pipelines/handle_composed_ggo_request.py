"""
TODO write this
"""
import logging
from celery import group

from origin.db import inject_session
from origin.tasks import celery_app
from origin.webhooks import WebhookService
from origin.auth import User, UserQuery
from origin.ggo import Ggo, GgoQuery

from .submit_batch_to_ledger import start_submit_batch_pipeline


webhook = WebhookService()


def start_handle_composed_ggo_pipeline(batch, recipients):
    """
    :param Batch batch:
    :param collections.abc.Iterable[(User, Ggo)] recipients:
    """
    on_submit_batch_complete = group(
        invoke_webhook.si(user.id, ggo.id) for ggo, user in recipients)

    start_submit_batch_pipeline(batch, on_submit_batch_complete)


@celery_app.task(name='compose.invoke_webhook')
@inject_session
def invoke_webhook(user_id, ggo_id, session):
    """
    :param int user_id:
    :param int ggo_id:
    :param Session session:
    """
    logging.info('--- compose.invoke_webhook, user_id=%d, ggo_id=%d' % (user_id, ggo_id))

    user = UserQuery(session) \
        .has_id(user_id) \
        .one()

    ggo = GgoQuery(session) \
        .has_id(ggo_id) \
        .one()

    webhook.on_ggo_received(user.sub, ggo)
