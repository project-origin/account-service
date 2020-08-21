import fire

from origin.auth import UserQuery
from origin.db import inject_session
from origin.ggo import GgoQuery
from origin.pipelines import (
    start_refresh_expiring_tokens_pipeline,
    start_refresh_token_for_subject_pipeline,
    start_import_technologies,
    start_import_meteringpoints,
    start_import_meteringpoints_for,
    start_invoke_on_ggo_received_tasks,
)


class PipelineTriggers(object):
    def refresh_expiring_tokens(self):
        start_refresh_expiring_tokens_pipeline()

    def refresh_token_for(self, subject):
        start_refresh_token_for_subject_pipeline(subject)

    def import_technologies(self):
        start_import_technologies()

    @inject_session
    def import_meteringpoints(self, session):
        start_import_meteringpoints(session)

    def import_meteringpoints_for(self, subject):
        start_import_meteringpoints_for(subject)

    @inject_session
    def trigger_ggo_received_webhooks_for(self, subject, session):
        user = UserQuery(session) \
            .has_sub(subject) \
            .one()

        ggos = GgoQuery(session) \
            .belongs_to(user) \
            .is_tradable()

        for ggo in ggos:
            start_invoke_on_ggo_received_tasks(
                subject=user.sub,
                ggo_id=ggo.id,
                session=session,
            )


if __name__ == '__main__':
    fire.Fire(PipelineTriggers)
