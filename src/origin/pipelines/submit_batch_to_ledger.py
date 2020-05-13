"""
TODO write this
"""
import origin_ledger_sdk as ols
from celery import chain

from origin import logger
from origin.db import atomic
from origin.tasks import celery_app
from origin.settings import LEDGER_URL, DEBUG
from origin.ledger import Batch


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
        submit_batch_to_ledger.si(batch_id=batch.id),
        poll_batch_status.s(batch_id=batch.id),
        # commit_or_rollback_batch.si(batch.id),
    )

    if callback:
        pipeline = chain(pipeline, callback)

    pipeline.apply_async()


@celery_app.task(
    bind=True,
    name='ledger.submit_batch_to_ledger',
    autoretry_for=(ols.LedgerException,),
    retry_backoff=2,
    max_retries=5,
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
    ledger = ols.Ledger(LEDGER_URL, verify=not DEBUG)
    batch = session \
        .query(Batch) \
        .filter(Batch.id == batch_id) \
        .one()

    # Submit batch
    try:
        with logger.tracer.span('ExecuteBatch'):
            handle = ledger.execute_batch(batch.build_ledger_batch())
    except ols.LedgerException as e:
        if e.code == 31:
            # Ledger Queue is full
            raise task.retry(
                max_retries=9999,
                countdown=SUBMIT_RETRY_DELAY,
            )
        else:
            logger.exception(f'Ledger raise an exception', extra={
                'subject': batch.user.sub,
                'batch_id': batch_id,
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
    autoretry_for=(ols.LedgerException,),
    retry_backoff=2,
    max_retries=5,
)
@logger.wrap_task(
    pipeline='submit_batch_to_ledger',
    task='poll_batch_status',
    title='Poll batch status',
)
@atomic
def poll_batch_status(task, handle, batch_id, session):
    """
    :param celery.Task task:
    :param str handle:
    :param int batch_id:
    :param Session session:
    """
    print('POLL BATCH STATUS, RETRIES: %d' % task.request.retries, flush=True)

    batch = session \
        .query(Batch) \
        .filter(Batch.id == batch_id) \
        .one()

    ledger = ols.Ledger(LEDGER_URL, verify=not DEBUG)

    with logger.tracer.span('GetBatchStatus'):
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
        raise task.retry(
            max_retries=MAX_POLLING_RETRIES,
            countdown=POLLING_DELAY,
        )
