"""
Asynchronous tasks for submitting a Batch to the ledger.
"""
import origin_ledger_sdk as ols
from celery import chain
from sqlalchemy import orm

from origin import logger
from origin.db import atomic, inject_session
from origin.tasks import celery_app
from origin.ledger import Batch
from origin.settings import LEDGER_URL, DEBUG, BATCH_RESUBMIT_AFTER_HOURS


# Settings
SUBMIT_RETRY_DELAY = 20
SUBMIT_MAX_RETRIES = (BATCH_RESUBMIT_AFTER_HOURS * 60 * 60) / SUBMIT_RETRY_DELAY

POLL_RETRY_DELAY = 10
POLL_MAX_RETRIES = (BATCH_RESUBMIT_AFTER_HOURS * 60 * 60) / POLL_RETRY_DELAY


# Services
ledger = ols.Ledger(LEDGER_URL, verify=not DEBUG)


def start_submit_batch_pipeline(subject, batch, success=None, error=None):
    """
    :param str subject:
    :param Batch batch:
    :param celery.Task success: Success callback task
    :param celery.Task error: Error callback task
    """
    pipeline = chain(
        submit_batch_to_ledger.si(subject=subject, batch_id=batch.id),
        batch_on_submitted.s(subject=subject, batch_id=batch.id),
        poll_batch_status.si(subject=subject, batch_id=batch.id),
        batch_on_commit.si(subject=subject, batch_id=batch.id),
    )

    error_pipeline = [
        batch_on_rollback.si(subject=subject, batch_id=batch.id),
    ]

    if error:
        error_pipeline.append(error)

    pipeline.apply_async(link=success, link_error=error_pipeline)


@celery_app.task(
    bind=True,
    name='submit_batch_to_ledger.submit_to_ledger',
    default_retry_delay=SUBMIT_RETRY_DELAY,
    max_retries=SUBMIT_MAX_RETRIES,
)
@logger.wrap_task(
    title='Submitting Batch to ledger',
    pipeline='submit_batch_to_ledger',
    task='submit_to_ledger',
)
@inject_session
def submit_batch_to_ledger(task, subject, batch_id, session):
    """
    :param celery.Task task:
    :param str subject:
    :param int batch_id:
    :param sqlalchemy.orm.Session session:
    """
    __log_extra = {
        'subject': subject,
        'batch_id': str(batch_id),
        'pipeline': 'submit_batch_to_ledger',
        'task': 'submit_to_ledger',
    }

    # Get Batch from DB
    try:
        batch = session \
            .query(Batch) \
            .filter(Batch.id == batch_id) \
            .one()
    except orm.exc.NoResultFound:
        raise
    except Exception as e:
        raise task.retry(exc=e)

    # Submit batch to ledger
    try:
        handle = ledger.execute_batch(batch.build_ledger_batch())
    except ols.LedgerConnectionError as e:
        logger.exception('Failed to submit batch to ledger', extra=__log_extra)
        raise task.retry(exc=e)
    except ols.LedgerException as e:
        if e.code in (15, 17, 18):
            logger.exception(f'Ledger validator error (code {e.code}), retrying...', extra=__log_extra)
            raise task.retry(exc=e)
        elif e.code == 31:
            logger.info(f'Ledger queue is full, retrying...', extra=__log_extra)
            raise task.retry(exc=e)
        else:
            raise

    logger.info(f'Batch submitted to ledger', extra=__log_extra)

    return handle


@celery_app.task(
    bind=True,
    name='submit_batch_to_ledger.batch_on_submitted',
    default_retry_delay=POLL_RETRY_DELAY,
    max_retries=POLL_MAX_RETRIES,
)
@logger.wrap_task(
    pipeline='submit_batch_to_ledger',
    task='batch_on_submitted',
    title='Batch.on_submitted()',
)
@atomic
def batch_on_submitted(task, handle, subject, batch_id, session):
    """
    :param celery.Task task:
    :param str handle:
    :param str subject:
    :param int batch_id:
    :param sqlalchemy.orm.Session session:
    """
    try:
        session \
            .query(Batch) \
            .filter(Batch.id == batch_id) \
            .one() \
            .on_submitted(handle)
    except orm.exc.NoResultFound:
        raise
    except Exception as e:
        logger.exception('Failed to invoke on_submitted() on Batch', extra={
            'subject': subject,
            'batch_id': str(batch_id),
            'pipeline': 'submit_batch_to_ledger',
            'task': 'batch_on_submitted',
        })
        raise task.retry(exc=e)


@celery_app.task(
    bind=True,
    name='submit_batch_to_ledger.poll_batch_status',
    default_retry_delay=POLL_RETRY_DELAY,
    max_retries=POLL_MAX_RETRIES,
)
@logger.wrap_task(
    pipeline='submit_batch_to_ledger',
    task='poll_batch_status',
    title='Poll batch status',
)
@atomic
def poll_batch_status(task, subject, batch_id, session):
    """
    :param celery.Task task:
    :param str subject:
    :param int batch_id:
    :param sqlalchemy.orm.Session session:
    """
    __log_extra = {
        'subject': subject,
        'batch_id': str(batch_id),
        'pipeline': 'submit_batch_to_ledger',
        'task': 'poll_batch_status',
    }

    class InvalidBatch(Exception):
        pass

    # Get batch from DB
    try:
        batch = session \
            .query(Batch) \
            .filter(Batch.id == batch_id) \
            .one()
    except orm.exc.NoResultFound:
        raise
    except Exception as e:
        logger.exception('Failed to load Batch from database', extra=__log_extra)
        raise task.retry(exc=e)

    # Get batch status from ledger
    try:
        response = ledger.get_batch_status(batch.handle)
    except ols.LedgerConnectionError as e:
        logger.exception('Failed to poll ledger for batch status', extra=__log_extra)
        raise task.retry(exc=e)

    # Assert status
    if response.status == ols.BatchStatus.COMMITTED:
        logger.info('Ledger batch status: COMMITTED', extra=__log_extra)
    elif response.status == ols.BatchStatus.INVALID:
        logger.error('Ledger batch status: INVALID', extra=__log_extra)
        # Raising exception triggers the ON ERROR task (rollback_batch())
        raise InvalidBatch('Invalid batch')
    elif response.status == ols.BatchStatus.UNKNOWN:
        logger.info('Ledger batch status: UNKNOWN', extra=__log_extra)
        raise task.retry()
    elif response.status == ols.BatchStatus.PENDING:
        logger.info('Ledger batch status: PENDING', extra=__log_extra)
        raise task.retry()
    else:
        raise RuntimeError('Unknown batch status returned, should NOT have happened!')


@celery_app.task(
    bind=True,
    name='submit_batch_to_ledger.batch_on_commit',
    default_retry_delay=POLL_RETRY_DELAY,
    max_retries=POLL_MAX_RETRIES,
)
@logger.wrap_task(
    pipeline='submit_batch_to_ledger',
    task='batch_on_commit',
    title='Batch.on_commit()',
)
@atomic
def batch_on_commit(task, subject, batch_id, session):
    """
    :param celery.Task task:
    :param str subject:
    :param int batch_id:
    :param sqlalchemy.orm.Session session:
    """
    try:
        session \
            .query(Batch) \
            .filter(Batch.id == batch_id) \
            .one() \
            .on_commit()
    except orm.exc.NoResultFound:
        raise
    except Exception as e:
        logger.exception('Failed to invoke on_commit() on Batch', extra={
            'subject': subject,
            'batch_id': str(batch_id),
            'pipeline': 'submit_batch_to_ledger',
            'task': 'batch_on_commit',
        })
        raise task.retry(exc=e)


@celery_app.task(
    bind=True,
    name='submit_batch_to_ledger.batch_on_rollback',
    default_retry_delay=POLL_RETRY_DELAY,
    max_retries=POLL_MAX_RETRIES,
)
@logger.wrap_task(
    pipeline='submit_batch_to_ledger',
    task='batch_on_rollback',
    title='Batch.on_rollback()',
)
@atomic
def batch_on_rollback(task, subject, batch_id, session):
    """
    :param celery.Task task:
    :param str subject:
    :param int batch_id:
    :param sqlalchemy.orm.Session session:
    """
    try:
        session \
            .query(Batch) \
            .filter(Batch.id == batch_id) \
            .one() \
            .on_rollback()
    except orm.exc.NoResultFound:
        raise
    except Exception as e:
        logger.exception('Failed to invoke on_rollback() on Batch', extra={
            'subject': subject,
            'batch_id': str(batch_id),
            'pipeline': 'submit_batch_to_ledger',
            'task': 'batch_on_rollback',
        })
        raise task.retry(exc=e)
