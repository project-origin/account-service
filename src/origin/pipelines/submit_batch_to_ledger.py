"""
TODO write this
"""
import logging
import origin_ledger_sdk as ols
from celery import chain

from origin.db import atomic
from origin.tasks import celery_app
from origin.settings import LEDGER_URL
from origin.ledger import Batch, logger

# Settings
POLLING_DELAY = 5
MAX_POLLING_RETRIES = int(3600 / POLLING_DELAY)
SUBMIT_RETRY_DELAY = 30


def start_submit_batch_pipeline(batch, callback=None):
    """
    :param Batch batch:
    :param Task callback:
    """
    pipeline = chain(
        submit_batch_to_ledger.si(batch.id),
        poll_batch_status.s(batch.id),
        # commit_or_rollback_batch.si(batch.id),
    )

    if callback:
        pipeline = chain(pipeline, callback)

    pipeline.apply_async()


@celery_app.task(
    bind=True,
    name='ledger.submit_batch_to_ledger',
    max_retries=None,
)
@logger.wrap_task(
    title='Submitting Batch to ledger',
    pipeline='submit_batch_to_ledger',
    task='submit_batch_to_ledger',
)
@atomic
def submit_batch_to_ledger(task, batch_id, session):
    """
    :param celery.Task task:
    :param int batch_id:
    :param Session session:
    """
    ledger = ols.Ledger(LEDGER_URL)
    batch = session \
        .query(Batch) \
        .filter(Batch.id == batch_id) \
        .one()

    # Submit batch
    try:
        handle = ledger.execute_batch(batch.build_ledger_batch())
    except ols.LedgerException as e:
        if e.code == 31:
            # Ledger Queue is full
            raise task.retry(countdown=SUBMIT_RETRY_DELAY)
        else:
            logger.exception(f'Ledger raise an exception', extra={
                'subject': batch.user.sub,
                'error_message': str(e),
                'error_code': e.code,
                'pipeline': 'import_measurements',
                'task': 'submit_to_ledger',
            })
            raise

    batch.on_submitted(handle)

    return handle


@celery_app.task(
    bind=True,
    name='ledger.poll_batch_status',
    max_retries=MAX_POLLING_RETRIES,
)
@logger.wrap_task(
    pipeline='submit_batch_to_ledger',
    task='poll_batch_status',
)
@atomic
def poll_batch_status(task, handle, batch_id, session):
    """
    :param celery.Task task:
    :param str handle:
    :param int batch_id:
    :param Session session:
    """
    batch = session \
        .query(Batch) \
        .filter(Batch.id == batch_id) \
        .one()

    ledger = ols.Ledger(LEDGER_URL)
    response = ledger.get_batch_status(handle)

    if response.status == ols.BatchStatus.COMMITTED:
        logger.error('Ledger submitted', extra={
            'subject': batch.user.sub,
            'handle': handle,
            'pipeline': 'import_measurements',
            'task': 'submit_to_ledger',
        })
        batch.on_commit()
    elif response.status == ols.BatchStatus.INVALID:
        logger.error('Batch submit FAILED: Invalid', extra={
            'subject': batch.user.sub,
            'handle': handle,
            'pipeline': 'import_measurements',
            'task': 'submit_to_ledger',
        })
        batch.on_rollback()
    else:
        raise task.retry(countdown=POLLING_DELAY)
