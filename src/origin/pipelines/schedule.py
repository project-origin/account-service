from celery.schedules import crontab

from origin.tasks import celery_app

from .resubmit_batches import resubmit_batches
from .refresh_access_token import get_soon_to_expire_tokens
from .import_technologies import import_technologies_and_insert_to_db


# The "wrapper" tasks exists because adding a shared_task()
# to the schedule causes a deadlock within Celery (known bug)

@celery_app.task()
def __resubmit_batches():
    resubmit_batches.s().apply_async()


@celery_app.task()
def __get_soon_to_expire_tokens():
    get_soon_to_expire_tokens.s().apply_async()


@celery_app.task()
def __import_technologies_and_insert_to_db():
    import_technologies_and_insert_to_db.s().apply_async()


# -- Schedule ----------------------------------------------------------------


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):

    # IMPORTANT: DO NOT ADD shared_task() TASKS HERE,
    # THEY CAUSE A DEADLOCK IN CELERY

    # RESUBMIT BATCHES TO THE LEDGER
    # Executes every hour
    sender.add_periodic_task(
        crontab(hour='*/1', minute=0),
        __resubmit_batches.s(),
    )

    # REFRESH ACCESS TOKENS
    # Refresh tokens every 30 minutes
    sender.add_periodic_task(
        crontab(minute='15,45'),
        __get_soon_to_expire_tokens.s(),
    )

    # IMPORT TECHNOLOGIES
    # Executes every night at 01:00
    sender.add_periodic_task(
        crontab(hour=1, minute=0),
        __import_technologies_and_insert_to_db.s(),
    )
