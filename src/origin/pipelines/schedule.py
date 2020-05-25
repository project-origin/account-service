from celery.schedules import crontab

from origin.tasks import celery_app

from .resubmit_batches import resubmit_batches
from .refresh_access_token import get_soon_to_expire_tokens
from .import_technologies import import_technologies_and_insert_to_db


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):

    # RESUBMIT BATCHES TO THE LEDGER
    # Executes every hour
    sender.add_periodic_task(
        crontab(hour='*/1', minute=0),
        resubmit_batches.s(),
    )

    # REFRESH ACCESS TOKENS
    # Refresh tokens every 30 minutes
    sender.add_periodic_task(
        crontab(minute='*/30'),
        get_soon_to_expire_tokens.s(),
    )

    # IMPORT TECHNOLOGIES
    # Executes every night at 01:00
    sender.add_periodic_task(
        crontab(hour=1, minute=0),
        import_technologies_and_insert_to_db.s(),
    )
