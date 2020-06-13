"""
Asynchronous tasks for importing GGOs from DataHubService.
Invokes the "GGO RECEIVED" webhook for each new GGO.

One entrypoint exists:

    start_import_issued_ggos()

"""
from celery import group, chain
from datetime import datetime
from sqlalchemy import orm

from origin import logger
from origin.db import inject_session, atomic
from origin.tasks import celery_app
from origin.auth import UserQuery
from origin.ggo import GgoImportController

from .webhooks import build_invoke_on_ggo_received_tasks


# Settings
RETRY_DELAY = 10
MAX_RETRIES = (24 * 60 * 60) / RETRY_DELAY


# Services
controller = GgoImportController()


def start_import_issued_ggos(subject, gsrn, begin):
    """
    :param str subject:
    :param str gsrn:
    :param datetime.datetime begin:
    """
    tasks = (
        import_ggos_and_insert_to_db.s(
            subject=subject,
            gsrn=gsrn,
            begin=begin.isoformat(),
        ),
        invoke_webhooks.s(
            subject=subject,
            gsrn=gsrn,
        ),
    )

    chain(*tasks).apply_async()


@celery_app.task(
    bind=True,
    name='import_ggos.import_ggos_and_insert_to_db',
    default_retry_delay=RETRY_DELAY,
    max_retries=MAX_RETRIES,
)
@logger.wrap_task(
    title='Importing GGOs for GSRN: %(gsrn)s',
    pipeline='import_ggos',
    task='import_ggos_and_insert_to_db',
)
@atomic
def import_ggos_and_insert_to_db(task, subject, gsrn, begin, session):
    """
    :param celery.Task task:
    :param str subject:
    :param str gsrn:
    :param str begin:
    :param sqlalchemy.orm.Session session:
    :rtype: list[int]
    :returns: A list of IDs of all new imported GGOs
    """
    __log_extra = {
        'subject': subject,
        'gsrn': gsrn,
        'begin': begin,
        'pipeline': 'import_ggos',
        'task': 'import_ggos_and_insert_to_db',
    }

    begin_dt = datetime.fromisoformat(begin)

    # Get User from DB
    try:
        user = UserQuery(session) \
            .has_sub(subject) \
            .has_gsrn(gsrn) \
            .one()
    except orm.exc.NoResultFound:
        raise
    except Exception as e:
        raise task.retry(exc=e)

    # Import GGOs
    try:
        ggos = controller.import_ggos(
            user=user,
            gsrn=gsrn,
            begin_from=begin_dt,
            begin_to=begin_dt,
            session=session,
        )
    except (controller.ImportError, controller.ImportConnectionError) as e:
        logger.exception(f'Failed to import GGOs, retrying...', extra=__log_extra)
        raise task.retry(exc=e)

    return [ggo.id for ggo in ggos]


@celery_app.task(
    name='import_ggos.invoke_webhooks',
    autoretry_for=(Exception,),
    default_retry_delay=RETRY_DELAY,
    max_retries=MAX_RETRIES,
)
@logger.wrap_task(
    title='Importing GGOs for GSRN: %(gsrn)s',
    pipeline='import_ggos',
    task='invoke_webhooks',
)
@inject_session
def invoke_webhooks(ggo_ids, subject, gsrn, session):
    """
    :param list[int] ggo_ids:
    :param str subject:
    :param str gsrn:
    :param sqlalchemy.orm.Session session:
    """
    __log_extra = {
        'subject': subject,
        'gsrn': gsrn,
        'pipeline': 'import_ggos',
        'task': 'invoke_webhooks',
    }

    tasks = []

    for ggo_id in ggo_ids:
        tasks.extend(build_invoke_on_ggo_received_tasks(
            subject=subject,
            ggo_id=ggo_id,
            session=session,
        ))

    if tasks:
        group(tasks).apply_async()
