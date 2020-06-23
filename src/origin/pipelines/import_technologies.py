"""
Asynchronous tasks for importing Technologies from DataHubService.

One entrypoint exists:

    start_import_technologies()

"""
from origin import logger
from origin.db import atomic
from origin.tasks import celery_app
from origin.ggo import Technology
from origin.services.datahub import DataHubService


# Settings
RETRY_DELAY = 60
MAX_RETRIES = (6 * 60 * 60) / RETRY_DELAY


# Services
datahub_service = DataHubService()


def start_import_technologies():
    import_technologies_and_insert_to_db \
        .s() \
        .apply_async()


@celery_app.task(
    name='import_technologies.import_technologies_and_insert_to_db',
    autoretry_for=(Exception,),
    default_retry_delay=RETRY_DELAY,
    max_retries=MAX_RETRIES,
)
@logger.wrap_task(
    title='Importing technologies from DataHub',
    pipeline='import_technologies',
    task='import_technologies_and_insert_to_db',
)
@atomic
def import_technologies_and_insert_to_db(session):
    """
    :param sqlalchemy.orm.Session session:
    """
    response = datahub_service.get_technologies()

    # Empty table
    session.query(Technology).delete()

    # Insert imported
    for technology in response.technologies:
        session.add(Technology(
            technology=technology.technology,
            technology_code=technology.technology_code,
            fuel_code=technology.fuel_code,
        ))
