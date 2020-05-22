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
RETRY_MAX_DELAY = 60
MAX_RETRIES = (24 * 60 * 60) / RETRY_MAX_DELAY


def start_submit_batch_pipeline(subject, batch, success=None, error=None):
    """
    :param str subject:
    :param Batch batch:
    :param celery.Task success: Success callback task
    :param celery.Task error: Error callback task
    """
    pipeline = chain(
        submit_batch_to_ledger.si(subject=subject, batch_id=batch.id),
        poll_batch_status.s(subject=subject, batch_id=batch.id),
    )

    error_pipeline = [
        rollback_batch.si(subject=subject, batch_id=batch.id),
    ]

    if error:
        error_pipeline.append(error)

    pipeline.apply_async(link=success, link_error=error_pipeline)


@celery_app.task(
    bind=True,
    name='ledger.submit_batch_to_ledger',
    autoretry_for=(Exception,),
    retry_backoff=2,
    retry_backoff_max=RETRY_MAX_DELAY,
    max_retries=MAX_RETRIES,
)
@logger.wrap_task(
    title='Submitting Batch to ledger',
    pipeline='submit_batch_to_ledger',
    task='submit_batch_to_ledger',
)
@atomic
def submit_batch_to_ledger(task, subject, batch_id, session):
    """
    :param celery.Task task:
    :param str subject:
    :param int batch_id:
    :param Session session:
    """
    ledger = ols.Ledger(LEDGER_URL, verify=not DEBUG)
    batch = session \
        .query(Batch) \
        .filter(Batch.id == batch_id) \
        .one()

    try:
        with logger.tracer.span('ExecuteBatch'):
            handle = ledger.execute_batch(batch.build_ledger_batch())
    except ols.LedgerException as e:
        # (e.code == 31) means Ledger Queue is full
        # In this case, don't log the error, just try again later
        if e.code != 31:
            logger.exception(f'Ledger raise an exception', extra={
                'subject': batch.user.sub,
                'batch_id': batch_id,
                'error_message': str(e),
                'error_code': e.code,
                'pipeline': 'import_measurements',
                'task': 'submit_to_ledger',
            })

        raise

    # Batch submitted successfully
    batch.on_submitted(handle)

    return handle


@celery_app.task(
    name='ledger.poll_batch_status',
    autoretry_for=(Exception,),
    retry_backoff=2,
    retry_backoff_max=RETRY_MAX_DELAY,
    max_retries=MAX_RETRIES,
)
@logger.wrap_task(
    pipeline='submit_batch_to_ledger',
    task='poll_batch_status',
    title='Poll batch status',
)
@atomic
def poll_batch_status(handle, subject, batch_id, session):
    """
    :param str handle:
    :param str subject:
    :param int batch_id:
    :param Session session:
    """
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
            'pipeline': 'submit_batch_to_ledger',
            'task': 'poll_batch_status',
        })
        batch.on_commit()
    elif response.status == ols.BatchStatus.INVALID:
        logger.error('Batch submit FAILED: Invalid', extra={
            'subject': batch.user.sub,
            'handle': handle,
            'pipeline': 'submit_batch_to_ledger',
            'task': 'poll_batch_status',
        })
        batch.on_rollback()
    elif response.status == ols.BatchStatus.UNKNOWN:
        logger.error('Batch submit UNKNOWN: Re-submitting', extra={
            'subject': batch.user.sub,
            'handle': handle,
            'pipeline': 'submit_batch_to_ledger',
            'task': 'poll_batch_status',
        })
        raise Exception('Retry task')
    else:
        raise Exception('Retry task')


@celery_app.task(
    name='ledger.rollback_batch',
    autoretry_for=(Exception,),
    retry_backoff=2,
    max_retries=16,
)
@logger.wrap_task(
    pipeline='submit_batch_to_ledger',
    task='rollback_batch',
    title='Rollback batch',
)
@atomic
def rollback_batch(subject, batch_id, session):
    """
    :param str subject:
    :param int batch_id:
    :param Session session:
    """
    batch = session \
        .query(Batch) \
        .filter(Batch.id == batch_id) \
        .one_or_none()

    if batch:
        batch.on_rollback()
