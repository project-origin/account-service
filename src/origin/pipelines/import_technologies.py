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


service = DataHubService()


def start_import_technologies():
    import_technologies_and_insert_to_db \
        .s() \
        .apply_async()


@celery_app.task(
    name='import_technologies.import_technologies_and_insert_to_db',
    autoretry_for=(Exception,),
    retry_backoff=2,
    max_retries=5,
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
    response = service.get_technologies()

    # Empty table
    session.query(Technology).delete()

    # Insert imported
    for technology in response.technologies:
        session.add(Technology(
            technology=technology.technology,
            technology_code=technology.technology_code,
            fuel_code=technology.fuel_code,
        ))
