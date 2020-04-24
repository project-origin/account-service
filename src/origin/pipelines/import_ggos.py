"""
TODO write this
"""
import logging
from celery import group
from datetime import datetime

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
        sub=request.sub,
        gsrn=request.gsrn,
        begin_from=request.begin_from.isoformat(),
        begin_to=request.begin_to.isoformat(),
    ).apply_async()


@celery_app.task(name='import_ggos.import_ggos_and_insert_to_db')
@inject_session
def import_ggos_and_insert_to_db(sub, gsrn, begin_from, begin_to, session):
    """
    :param str sub:
    :param str gsrn:
    :param str begin_from:
    :param str begin_to:
    :param Session session:
    """
    logging.info((
        '--- import_ggos_and_insert_to_db, '
        'sub=%s, gsrn=%s, begin_from=%s, begin_to=%s'
    ) % (sub, gsrn, begin_from, begin_to))

    user = UserQuery(session) \
        .has_sub(sub) \
        .has_gsrn(gsrn) \
        .one_or_none()

    if user is None:
        return

    begin_from = datetime.fromisoformat(begin_from)
    begin_to = datetime.fromisoformat(begin_to)

    ggos = controller.import_ggos(user, gsrn, begin_from, begin_to)
    tasks = [invoke_webhook.si(sub, ggo.id) for ggo in ggos]

    if tasks:
        group(tasks).apply_async()


@celery_app.task(name='import_ggos.invoke_webhook')
@inject_session
def invoke_webhook(sub, ggo_id, session):
    """
    :param str sub:
    :param int ggo_id:
    :param Session session:
    """
    logging.info('--- invoke_webhook, sub=%s, ggo_id=%d' % (sub, ggo_id))

    ggo = GgoQuery(session) \
        .has_id(ggo_id) \
        .one()

    webhook.on_ggo_received(sub, ggo)
