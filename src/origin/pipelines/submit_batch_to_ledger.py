"""
TODO write this
"""
import logging
import origin_ledger_sdk as ols
from celery import chain

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
@atomic
def submit_batch_to_ledger(task, batch_id, session):
    """
    :param celery.Task task:
    :param int batch_id:
    :param Session session:
    """
    logging.info('--- submit_batch_to_ledger, batch_id = %d' % batch_id)

    ledger = ols.Ledger(LEDGER_URL, verify=not DEBUG)
    batch = session \
        .query(Batch) \
        .filter(Batch.id == batch_id) \
        .one()

    # Submit batch
    try:
        handle = ledger.execute_batch(batch.build_ledger_batch())
    except ols.LedgerException as e:
        if e.code == 31:
            logging.info('ERROR 31, RETRYING...')
            # Ledger queue is full, try again later
            raise task.retry(countdown=SUBMIT_RETRY_DELAY)
        else:
            raise e

    batch.on_submitted(handle)

    return handle


@celery_app.task(
    bind=True,
    name='ledger.poll_batch_status',
    max_retries=MAX_POLLING_RETRIES,
)
@atomic
def poll_batch_status(task, handle, batch_id, session):
    """
    :param celery.Task task:
    :param str handle:
    :param int batch_id:
    :param Session session:
    """
    logging.info('--- poll_batch_status, batch_id = %d' % batch_id)

    batch = session \
        .query(Batch) \
        .filter(Batch.id == batch_id) \
        .one()

    # @atomic
    # def __increment_poll_count(session):
    #     session \
    #         .query(Batch) \
    #         .filter(Batch.id == batch_id) \
    #         .update({'poll_count': Batch.poll_count + 1})

    ledger = ols.Ledger(LEDGER_URL, verify=not DEBUG)
    response = ledger.get_batch_status(handle)

    if response.status == ols.BatchStatus.COMMITTED:
        batch.on_commit()
    elif response.status == ols.BatchStatus.INVALID:
        batch.on_rollback()
    else:
        raise task.retry(countdown=POLLING_DELAY)

    # # Only check handle if the batch has been submitted
    # # and isn't already completed or declined
    # if batch.state == BatchState.SUBMITTED:
    #     state = processor.check_batch_status(batch)
    #
    #     if state == LedgerState.COMMITTED:
    #         batch.on_commit()
    #     elif state == LedgerState.INVALID:
    #         batch.on_rollback()
    #     elif state == LedgerState.PENDING:
    #         __increment_poll_count()
    #         raise task.retry(countdown=batch.get_poll_delay())
    #     elif state == LedgerState.UNKNOWN:
    #         __increment_poll_count()
    #         # TODO WHAT TO DO?
    #         raise task.retry(countdown=batch.get_poll_delay())
