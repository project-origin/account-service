"""
Asynchronous tasks for importing MeteringPoints from DataHubService.

One entrypoint exists:

    start_import_meteringpoints()

"""
from sqlalchemy import orm
from celery import group, shared_task

from origin import logger
from origin.db import atomic, inject_session
from origin.services.datahub import (
    DataHubService,
    DataHubServiceError,
    DataHubServiceConnectionError,
)
from origin.auth import (
    UserQuery,
    MeteringPointQuery,
    MeteringPoint,
)


# Settings
RETRY_DELAY = 10
MAX_RETRIES = (24 * 60 * 60) / RETRY_DELAY


# Services
datahub_service = DataHubService()


def start_import_meteringpoints(subject):
    """
    :param str subject:
    """
    import_meteringpoints_and_insert_to_db \
        .s(subject=subject) \
        .apply_async()


@shared_task(
    bind=True,
    name='import_meteringpoints.import_meteringpoints_and_insert_to_db',
    default_retry_delay=RETRY_DELAY,
    max_retries=MAX_RETRIES,
)
@logger.wrap_task(
    title='Importing meteringpoints from DataHub',
    pipeline='import_meteringpoints',
    task='import_meteringpoints_and_insert_to_db',
)
@inject_session
def import_meteringpoints_and_insert_to_db(task, subject, session):
    """
    :param celery.Task task:
    :param str subject:
    :param sqlalchemy.orm.Session session:
    """
    __log_extra = {
        'subject': subject,
        'pipeline': 'import_meteringpoints',
        'task': 'import_meteringpoints_and_insert_to_db',
    }

    # Get User from DB
    try:
        user = UserQuery(session) \
            .has_sub(subject) \
            .one()
    except orm.exc.NoResultFound:
        raise
    except Exception as e:
        logger.exception('Failed to load User from database, retrying...', extra=__log_extra)
        raise task.retry(exc=e)

    # Import MeteringPoints from DataHubService
    try:
        response = datahub_service.get_meteringpoints(user.access_token)
    except DataHubServiceConnectionError as e:
        logger.exception(f'Failed to establish connection to DataHubService, retrying...', extra=__log_extra)
        raise task.retry(exc=e)
    except DataHubServiceError as e:
        if e.status_code == 400:
            logger.exception('Got BAD REQUEST from DataHubService', extra=__log_extra)
            raise
        else:
            logger.exception('Failed to import MeteringPoints, retrying...', extra=__log_extra)
            raise task.retry(exc=e)

    # Save imported MeteringPoints to database
    try:
        meteringpoints = save_imported_meteringpoints(user, response)
    except Exception as e:
        logger.exception('Failed to save imported Meteringpoints to database, retrying...', extra=__log_extra)
        raise task.retry(exc=e)

    logger.info(f'Imported {len(meteringpoints)} new MeteringPoints from DataHubService', extra=__log_extra)

    # Send MeteringPoint key to DataHubService for each imported MeteringPoint
    tasks = []

    for meteringpoint in meteringpoints:
        logger.info(f'Imported meteringpoint with GSRN: {meteringpoint.gsrn}', extra={
            'gsrn': meteringpoint.gsrn,
            'subject': user.sub,
            'pipeline': 'import_meteringpoints',
            'task': 'import_meteringpoints_and_insert_to_db',
        })

        tasks.append(send_key_to_datahub_service.s(
            subject=subject,
            gsrn=meteringpoint.gsrn,
        ))

    group(*tasks).apply_async()


@shared_task(
    bind=True,
    name='import_meteringpoints.send_key_to_datahub_service',
    default_retry_delay=RETRY_DELAY,
    max_retries=MAX_RETRIES,
)
@logger.wrap_task(
    title='Sending key for MeteringPoint to DataHubService',
    pipeline='import_meteringpoints',
    task='send_key_to_datahub_service',
)
@inject_session
def send_key_to_datahub_service(task, subject, gsrn, session):
    """
    :param celery.Task task:
    :param str subject:
    :param str gsrn:
    :param sqlalchemy.orm.Session session:
    """
    __log_extra = {
        'subject': subject,
        'gsrn': gsrn,
        'pipeline': 'import_meteringpoints',
        'task': 'send_key_to_datahub_service',
    }

    # Get User from DB
    try:
        user = UserQuery(session) \
            .has_sub(subject) \
            .one()
    except orm.exc.NoResultFound:
        raise
    except Exception as e:
        logger.exception('Failed to load User from database, retrying...', extra=__log_extra)
        raise task.retry(exc=e)

    # Get MeteringPoint from DB
    try:
        meteringpoint = MeteringPointQuery(session) \
            .has_gsrn(gsrn) \
            .one()
    except orm.exc.NoResultFound:
        raise
    except Exception as e:
        logger.exception('Failed to load MeteringPoint from database, retrying...', extra=__log_extra)
        raise task.retry(exc=e)

    # Send key to DataHubService
    try:
        datahub_service.set_key(
            token=user.access_token,
            gsrn=meteringpoint.gsrn,
            key=meteringpoint.extended_key,
        )
    except DataHubServiceConnectionError as e:
        logger.exception(f'Failed to establish connection to DataHubService, retrying...', extra=__log_extra)
        raise task.retry(exc=e)
    except DataHubServiceError as e:
        if e.status_code == 400:
            logger.exception('Got BAD REQUEST from DataHubService', extra=__log_extra)
            raise
        else:
            logger.exception('Failed to import MeteringPoints, retrying...', extra=__log_extra)
            raise task.retry(exc=e)


# -- Helper functions --------------------------------------------------------


@atomic
def save_imported_meteringpoints(user, response, session):
    """
    :param origin.auth.User user:
    :param origin.services.datahub.GetMeteringPointsResponse response:
    :param sqlalchemy.orm.Session session:
    :rtype: list[MeteringPoint]
    """
    imported_meteringpoints = []

    for meteringpoint in response.meteringpoints:
        count = MeteringPointQuery(session) \
            .has_gsrn(meteringpoint.gsrn) \
            .count()

        if count > 0:
            logger.info(f'Skipping meteringpoint with GSRN: {meteringpoint.gsrn} (already exists in DB)', extra={
                'subject': user.sub,
                'gsrn': meteringpoint.gsrn,
                'pipeline': 'import_meteringpoints',
                'task': 'import_meteringpoints_and_insert_to_db',
            })
            continue

        imported_meteringpoints.append(MeteringPoint.create(
            user=user,
            gsrn=meteringpoint.gsrn,
            sector=meteringpoint.sector,
            session=session,
        ))

    session.add_all(imported_meteringpoints)
    session.flush()

    return imported_meteringpoints
