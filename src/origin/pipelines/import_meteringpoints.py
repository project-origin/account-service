"""
TODO write this
"""
import logging

from origin.db import atomic
from origin.tasks import celery_app
from origin.services.datahub import DataHubService
from origin.auth import (
    UserQuery,
    MeteringPointQuery,
    MeteringPoint,
    MeteringPointIndexSequence,
)


service = DataHubService()


def start_import_meteringpoints(user_id):
    """
    :param int user_id:
    """
    import_meteringpoints_and_insert_to_db.s(user_id) \
        .apply_async()


@celery_app.task(name='import_meteringpoints.import_meteringpoints_and_insert_to_db')
@atomic
def import_meteringpoints_and_insert_to_db(user_id, session):
    """
    :param int user_id:
    :param Session session:
    """
    logging.info('--- import_meteringpoints.import_meteringpoints_and_insert_to_db, user_id=%d' % user_id)

    user = UserQuery(session) \
        .has_id(user_id) \
        .one()

    response = service.get_meteringpoints(user.access_token)

    for meteringpoint in response.meteringpoints:
        count = MeteringPointQuery(session) \
            .belongs_to(user) \
            .has_gsrn(meteringpoint.gsrn) \
            .count()

        if count == 0:
            meteringpoint = MeteringPoint.create(
                user=user,
                gsrn=meteringpoint.gsrn,
                sector=meteringpoint.sector,
            )

            session.add(meteringpoint)

            service.set_key(
                token=user.access_token,
                gsrn=meteringpoint.gsrn,
                key=meteringpoint.extended_key,
            )
