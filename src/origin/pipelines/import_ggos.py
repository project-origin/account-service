"""
TODO write this
"""
from celery import group
from datetime import datetime

from origin import logger
from origin.db import inject_session
from origin.tasks import celery_app
from origin.webhooks import WebhookService
from origin.auth import UserQuery
from origin.ggo import (
    GgoQuery,
    GgoIssueController,
    OnGgosIssuedWebhookRequest,
)


webhook = WebhookService()
controller = GgoIssueController()


def start_import_issued_ggos(request):
    """
    :param OnGgosIssuedWebhookRequest request:
    """
    import_ggos_and_insert_to_db \
        .s(
            subject=request.sub,
            gsrn=request.gsrn,
            begin=request.begin.isoformat(),
        ) \
        .apply_async()


@celery_app.task(
    name='import_ggos.import_ggos_and_insert_to_db',
    autoretry_for=(Exception,),
    retry_backoff=2,
    max_retries=5,
)
@logger.wrap_task(
    title='Importing GGOs for GSRN: %(gsrn)s',
    pipeline='import_ggos',
    task='import_ggos_and_insert_to_db',
)
@inject_session
def import_ggos_and_insert_to_db(subject, gsrn, begin, session):
    """
    :param str subject:
    :param str gsrn:
    :param str begin:
    :param Session session:
    """
    user = UserQuery(session) \
        .has_sub(subject) \
        .has_gsrn(gsrn) \
        .one_or_none()

    if user is None:
        return

    begin = datetime.fromisoformat(begin)
    ggos = controller.import_ggos(user, gsrn, begin, begin)
    tasks = [invoke_webhook.si(subject=subject, ggo_id=ggo.id) for ggo in ggos]

    if tasks:
        group(tasks).apply_async()


@celery_app.task(
    name='import_ggos.invoke_webhook',
    autoretry_for=(Exception,),
    retry_backoff=2,
    max_retries=5,
)
@logger.wrap_task(
    title='Invoking webhook on_ggo_received',
    pipeline='import_ggos',
    task='invoke_webhook',
)
@inject_session
def invoke_webhook(subject, ggo_id, session):
    """
    :param str subject:
    :param int ggo_id:
    :param Session session:
    """
    ggo = GgoQuery(session) \
        .has_id(ggo_id) \
        .one_or_none()

    webhook.on_ggo_received(subject, ggo)
