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
    import_ggos_and_insert_to_db.s(
        subject=request.sub,
        gsrn=request.gsrn,
        begin_from=request.begin_from.isoformat(),
        begin_to=request.begin_to.isoformat(),
    ).apply_async()


@celery_app.task(name='import_ggos.import_ggos_and_insert_to_db')
@logger.wrap_task(
    title='Importing GGOs for GSRN: %(gsrn)s',
    pipeline='import_ggos',
    task='import_ggos_and_insert_to_db',
)
@inject_session
def import_ggos_and_insert_to_db(subject, gsrn, begin_from, begin_to, session):
    """
    :param str subject:
    :param str gsrn:
    :param str begin_from:
    :param str begin_to:
    :param Session session:
    """
    user = UserQuery(session) \
        .has_sub(subject) \
        .has_gsrn(gsrn) \
        .one_or_none()

    if user is None:
        return

    begin_from = datetime.fromisoformat(begin_from)
    begin_to = datetime.fromisoformat(begin_to)

    ggos = controller.import_ggos(user, gsrn, begin_from, begin_to)
    tasks = [invoke_webhook.si(subject=subject, ggo_id=ggo.id) for ggo in ggos]

    if tasks:
        group(tasks).apply_async()


@celery_app.task(name='import_ggos.invoke_webhook')
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
        .one()

    webhook.on_ggo_received(subject, ggo)
