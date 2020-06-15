from origin import logger
from origin.common import DateTimeRange
from origin.services.datahub import DataHubService, GetGgoListRequest

from .models import Ggo
from .queries import GgoQuery


datahub_service = DataHubService()


class GgoImportController(object):
    """
    Imports GGO(s) from DataHubService and saves them in the
    database with an ISSUED state.
    """
    def import_ggos(self, user, gsrn, begin_from, begin_to, session):
        """
        :param User user:
        :param str gsrn:
        :param datetime.datetime begin_from:
        :param datetime.datetime begin_to:
        :param sqlalchemy.orm.Session session:
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

        # Import GGOs from DataHub
        imported_ggos = self.fetch_ggos(user, gsrn, begin_from, begin_to)
        mapped_ggos = (self.map_imported_ggo(user, ggo) for ggo in imported_ggos)
        filtered_ggos = (
            ggo for ggo in mapped_ggos
            if not self.ggo_exists(ggo.address, session)
        )

        new_ggos = []

        # Filter out GGOs that already exists and map to Ggo type
        for ggo in filtered_ggos:
            session.add(ggo)
            session.flush()
            new_ggos.append(ggo)

        logger.info(f'Imported {len(new_ggos)} GGOs for GSRN: {gsrn}', extra={
            'gsrn': gsrn,
            'subject': user.sub,
            'begin_from': str(begin_from),
            'begin_to': str(begin_to),
            'pipeline': 'import_ggos',
            'task': 'import_ggos_and_insert_to_db',
        })

        return new_ggos

    def fetch_ggos(self, user, gsrn, begin_from, begin_to):
        """
        :param User user:
        :param str gsrn:
        :param datetime.datetime begin_from:
        :param datetime.datetime begin_to:
        :rtype: list[origin.services.datahub.Ggo]
        """
        begin_range = DateTimeRange(begin=begin_from, end=begin_to)
        request = GetGgoListRequest(gsrn=gsrn, begin_range=begin_range)
        response = datahub_service.get_ggo_list(user.access_token, request)
        return response.ggos

    def ggo_exists(self, address, session):
        """
        :param str address:
        :param sqlalchemy.orm.Session session:
        """
        count = GgoQuery(session) \
            .has_address(address) \
            .count()

        return count > 0

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
            end=imported_ggo.end,
            amount=imported_ggo.amount,
            sector=imported_ggo.sector,
            technology_code=imported_ggo.technology_code,
            fuel_code=imported_ggo.fuel_code,
            synchronized=True,
            issued=True,
            stored=True,
            locked=False,
            issue_gsrn=imported_ggo.gsrn,
        )
