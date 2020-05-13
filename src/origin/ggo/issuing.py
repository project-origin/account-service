from origin import logger
from origin.db import atomic
from origin.ggo import GgoQuery, Ggo
from origin.common import DateTimeRange
from origin.services.datahub import DataHubService, GetGgoListRequest


datahub = DataHubService()


class GgoIssueController(object):
    """
    TODO
    """

    def import_ggos(self, user, gsrn, begin_from, begin_to):
        """
        :param User user:
        :param str gsrn:
        :param datetime.datetime begin_from:
        :param datetime.datetime begin_to:
        :rtype: list[Ggo]
        """
        logger.info(f'Importing GGOs for GSRN: {gsrn}', extra={
            'gsrn': gsrn,
            'subject': user.sub,
            'begin_from': str(begin_from),
            'begin_to': str(begin_to),
            'pipeline': 'import_ggos',
            'task': 'import_ggos_and_insert_to_db',
        })

        imported_ggos = self.fetch_ggos(user, gsrn, begin_from, begin_to)
        issued_ggos = self.insert_to_db(user, imported_ggos)

        logger.info(f'Imported {len(issued_ggos)} GGOs for GSRN: {gsrn}', extra={
            'gsrn': gsrn,
            'subject': user.sub,
            'begin_from': str(begin_from),
            'begin_to': str(begin_to),
            'pipeline': 'import_ggos',
            'task': 'import_ggos_and_insert_to_db',
        })

        return issued_ggos

    def fetch_ggos(self, user, gsrn, begin_from, begin_to):
        """
        :param User user:
        :param str gsrn:
        :param datetime.datetime begin_from:
        :param datetime.datetime begin_to:
        :rtype: list[Ggo]
        """
        begin_range = DateTimeRange(begin=begin_from, end=begin_to)
        request = GetGgoListRequest(gsrn=gsrn, begin_range=begin_range)
        response = datahub.get_ggo_list(user.access_token, request)
        return response.ggos

    @atomic
    def insert_to_db(self, user, imported_ggos, session):
        """
        :param User user:
        :param list[origin.services.datahub.Ggo] imported_ggos:
        :param Session session:
        :rtype: list[Ggo]
        """
        ggos = []

        for i, imported_ggo in enumerate(imported_ggos):
            count = GgoQuery(session) \
                .has_address(imported_ggo.address) \
                .count()

            if count == 0:
                ggo = self.map_imported_ggo(user, imported_ggo)
                session.add(ggo)
                ggos.append(ggo)

                if i % 100 == 0:
                    session.flush()

        return ggos

    def map_imported_ggo(self, user, imported_ggo):
        """
        :param User user:
        :param origin.services.datahub.Ggo imported_ggo:
        :rtype: Ggo
        """
        return Ggo(
            user_id=user.id,
            address=imported_ggo.address,
            issue_time=imported_ggo.issue_time,
            expire_time=imported_ggo.expire_time,
            begin=imported_ggo.begin,
            amount=imported_ggo.amount,
            sector=imported_ggo.sector,
            end=imported_ggo.end,
            technology_code=imported_ggo.technology_code,
            fuel_code=imported_ggo.fuel_code,
            synchronized=True,
            issued=True,
            stored=True,
            locked=False,
            issue_gsrn=imported_ggo.gsrn,
        )
