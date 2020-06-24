"""
Asynchronous tasks for submitting a composed GGO to the ledger.
Invokes the "GGO RECEIVED" webhook on completion.

One entrypoint exists:

    start_handle_composed_ggo_pipeline()

"""
from celery import group

from .webhooks import build_invoke_on_ggo_received_tasks
from .submit_batch_to_ledger import start_submit_batch_pipeline


def start_handle_composed_ggo_pipeline(batch, recipients, session):
    """
    :param origin.ledger.Batch batch:
    :param collections.abc.Iterable[(origin.auth.User, origin.ggo.Ggo)] recipients:
    :param sqlalchemy.orm.Session session:
    :rtype: celery.result.AsyncResult
    """
    on_success_tasks = []

    # On success, invoke a webhook GgoReceived for each recipient of a GGO
    for user, ggo in recipients:
        on_success_tasks.extend(build_invoke_on_ggo_received_tasks(
            subject=user.sub,
            ggo_id=ggo.id,
            session=session,
            batch_id=batch.id,
        ))

    # Start pipeline
    return start_submit_batch_pipeline(
        subject=batch.user.sub,
        batch=batch,
        success=group(*on_success_tasks) if on_success_tasks else None,
    )
