"""
Resubmits unpublished batches to the ledger. These are the Batches
which has not been successfully submitted to the ledger for some reason,
for instance if the ledger has been down for a period of time etc.
"""
import sqlalchemy as sa
from sqlalchemy import text

from origin import logger
from origin.db import inject_session
from origin.tasks import celery_app
from origin.ledger import Batch, BatchState
from origin.settings import BATCH_RESUBMIT_AFTER_HOURS

from .submit_batch_to_ledger import start_submit_batch_pipeline


def start_resubmit_batches_pipeline():
    """
    TODO
    """
    resubmit_batches \
        .s() \
        .apply_async()


@celery_app.task(
    name='resubmit_batches.resubmit_batches',
    autoretry_for=(Exception,),
    retry_backoff=2,
    max_retries=5,
)
@logger.wrap_task(
    title='Resubmitting batches',
    pipeline='resubmit_batches',
    task='resubmit_batches',
)
@inject_session
def resubmit_batches(session):
    """
    :param Session session:
    """
    batches = session.query(Batch) \
        .filter(
            sa.or_(
                sa.and_(
                    Batch.state == BatchState.PENDING,
                    Batch.created <= text(
                        "NOW() - INTERVAL '%d HOURS'" % BATCH_RESUBMIT_AFTER_HOURS),
                ),
                sa.and_(
                    Batch.state == BatchState.SUBMITTED,
                    Batch.submitted <= text(
                        "NOW() - INTERVAL '%d HOURS'" % BATCH_RESUBMIT_AFTER_HOURS),
                ),
            ),
        )

    for batch in batches:
        start_submit_batch_pipeline(
            subject=batch.user.sub,
            batch=batch,
        )
