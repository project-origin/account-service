"""
Asynchronous tasks for importing MeteringPoints from DataHubService.

One entrypoint exists:

    start_import_meteringpoints()

"""
from origin import logger
from origin.db import atomic
from origin.tasks import celery_app
from origin.services.datahub import DataHubService
from origin.auth import (
    UserQuery,
    MeteringPointQuery,
    MeteringPoint,
)


service = DataHubService()


def start_import_meteringpoints(user):
    """
    :param User user:
    """
    import_meteringpoints_and_insert_to_db \
        .s(subject=user.sub) \
        .apply_async()


@celery_app.task(
    name='import_meteringpoints.import_meteringpoints_and_insert_to_db',
    autoretry_for=(Exception,),
    retry_backoff=2,
    retry_backoff_max=30,
    max_retries=20,
)
@logger.wrap_task(
    title='Importing meteringpoints from DataHub',
    pipeline='import_meteringpoints',
    task='import_meteringpoints_and_insert_to_db',
)
@atomic
def import_meteringpoints_and_insert_to_db(subject, session):
    """
    :param str subject:
    :param sqlalchemy.orm.Session session:
    """

    user = UserQuery(session) \
        .has_sub(subject) \
        .one()

    response = service.get_meteringpoints(user.access_token)

    for meteringpoint in response.meteringpoints:
        count = MeteringPointQuery(session) \
            .has_gsrn(meteringpoint.gsrn) \
            .count()

        if count > 0:
            logger.info(f'Skipping meteringpoint with GSRN: {meteringpoint.gsrn} (already exists in DB)', extra={
                'gsrn': meteringpoint.gsrn,
                'subject': user.sub,
                'pipeline': 'import_meteringpoints',
                'task': 'import_meteringpoints_and_insert_to_db',
            })
            continue

        meteringpoint = MeteringPoint.create(
            user=user,
            gsrn=meteringpoint.gsrn,
            sector=meteringpoint.sector,
            session=session,
        )

        session.add(meteringpoint)
        session.flush()

        logger.info(f'Imported meteringpoint with GSRN: {meteringpoint.gsrn}', extra={
            'gsrn': meteringpoint.gsrn,
            'subject': user.sub,
            'pipeline': 'import_meteringpoints',
            'task': 'import_meteringpoints_and_insert_to_db',
        })

        service.set_key(
            token=user.access_token,
            gsrn=meteringpoint.gsrn,
            key=meteringpoint.extended_key,
        )
