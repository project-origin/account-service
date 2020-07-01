import fire

from origin.db import inject_session
from origin.pipelines import (
    start_refresh_expiring_tokens_pipeline,
    start_refresh_token_for_subject_pipeline,
    start_import_technologies,
    start_import_meteringpoints,
    start_import_meteringpoints_for,
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


if __name__ == '__main__':
    fire.Fire(PipelineTriggers)
