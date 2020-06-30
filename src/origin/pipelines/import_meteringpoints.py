"""
Asynchronous tasks for importing MeteringPoints from DataHubService.

Two entrypoints exists:

    start_import_meteringpoints()
    start_import_meteringpoints_for(subject)

"""
from sqlalchemy import orm
from celery import group, shared_task

from origin import logger
from origin.auth import UserQuery
from origin.db import atomic, inject_session
from origin.services.datahub import (
    DataHubService,
    DataHubServiceError,
    DataHubServiceConnectionError,
    MeteringPointType as DataHubMeteringPointType,
)
from origin.auth import (
    UserQuery,
    MeteringPointQuery,
    MeteringPoint,
    MeteringPointType,
)


# Settings
RETRY_DELAY = 10
MAX_RETRIES = (24 * 60 * 60) / RETRY_DELAY


# Services
datahub_service = DataHubService()


def start_import_meteringpoints(session):
    """
    Imports (or updates) MeteringPoints for all users.

    :param sqlalchemy.orm.Session session:
    """
    for user in UserQuery(session).all():
        start_import_meteringpoints_for(user.sub)


def start_import_meteringpoints_for(subject):
    """
    Imports (or updates) MeteringPoints for a single user.

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
            raise
        else:
            logger.exception('Failed to import MeteringPoints, retrying...', extra=__log_extra)
            raise task.retry(exc=e)


# -- Helper functions --------------------------------------------------------


@atomic
def save_imported_meteringpoints(user, response, session):
    """
    Creates MeteringPoints imported from DataHubService in the database.
    If they already exists, updates their type (consumption or production).

    :param origin.auth.User user:
    :param origin.services.datahub.GetMeteringPointsResponse response:
    :param sqlalchemy.orm.Session session:
    :rtype: list[MeteringPoint]
    """
    imported_meteringpoints = []

    for meteringpoint in response.meteringpoints:
        existing_meteringpoint = MeteringPointQuery(session) \
            .has_gsrn(meteringpoint.gsrn) \
            .one_or_none()

        if meteringpoint.type is DataHubMeteringPointType.PRODUCTION:
            typ = MeteringPointType.PRODUCTION
        elif meteringpoint.type is DataHubMeteringPointType.CONSUMPTION:
            typ = MeteringPointType.CONSUMPTION
        else:
            raise RuntimeError('Should NOT have happened!')

        if existing_meteringpoint:
            logger.info(f'MeteringPoint {meteringpoint.gsrn} already exists in DB (updating type)', extra={
                'subject': user.sub,
                'gsrn': meteringpoint.gsrn,
                'type': meteringpoint.type.value,
                'pipeline': 'import_meteringpoints',
                'task': 'import_meteringpoints_and_insert_to_db',
            })
            existing_meteringpoint.type = typ
        else:
            imported_meteringpoints.append(MeteringPoint.create(
                user=user,
                gsrn=meteringpoint.gsrn,
                sector=meteringpoint.sector,
                type=typ,
                session=session,
            ))

    session.add_all(imported_meteringpoints)
    session.flush()

    return imported_meteringpoints
