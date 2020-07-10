from datetime import datetime
from itertools import groupby

from origin.ggo import GgoQuery, Ggo
from origin.common import DateTimeRange
from origin.auth import MeteringPoint, User
from origin.services.energytypes import EnergyTypeService, EmissionData
from origin.services.datahub import (
    DataHubService,
    GetMeasurementListRequest,
    Measurement,
    MeasurementType,
    MeasurementFilters,
)

from .models import EcoDeclarationResolution
from .declaration import EcoDeclaration, EmissionValues


datahub_service = DataHubService()
energytype_service = EnergyTypeService()


class EcoDeclarationBuilder(object):
    """
    TODO
    """

    def build_eco_declaration(self, user, meteringpoints, begin_from, begin_to, session):
        """
        :param User user:
        :param list[MeteringPoint] meteringpoints:
        :param datetime begin_from:
        :param datetime begin_to:
        :param sqlalchemy.orm.Session session:
        :rtype: (EcoDeclaration, EcoDeclaration)
        :returns: A tuple of (individual declaration, general declaration)
        """
        assert len(meteringpoints) > 0

        # -- Dependencies ----------------------------------------------------

        measurements = self.get_measurements(
            user, meteringpoints, begin_from, begin_to)

        retired_ggos = self.get_retired_ggos(
            meteringpoints, session)

        general_mix_emissions = self.get_general_mix(
            meteringpoints, begin_from, begin_to)

        # -- Declarations ----------------------------------------------------

        general = self.build_general_declaration(
            measurements, general_mix_emissions)

        individual = self.build_individual_declaration(
            measurements, retired_ggos, general_mix_emissions)

        return individual, general

    def build_individual_declaration(self, measurements, retired_ggos, general_mix_emissions):
        """
        :param list[Measurement] measurements:
        :param dict[str, dict[datetime, list[Ggo]]] retired_ggos:
        :param dict[str, dict[datetime, EmissionData]] general_mix_emissions:
        :rtype: EcoDeclaration
        """

        # Emission in gram (mapped by begin)
        emissions = {}

        # Consumption in Wh (mapped by begin)
        consumed_amount = {}

        for m in measurements:
            ggos = retired_ggos.get(m.gsrn, {}).get(m.begin, [])
            ggos_with_emissions = [ggo for ggo in ggos if ggo.emissions]
            retired_amount = sum(ggo.amount for ggo in ggos_with_emissions)
            remaining_amount = m.amount - retired_amount

            assert 0 <= retired_amount <= m.amount
            assert 0 <= remaining_amount <= m.amount
            assert retired_amount + remaining_amount == m.amount

            # Consumed amount
            consumed_amount.setdefault(m.begin, 0)
            consumed_amount[m.begin] += m.amount

            # Emission from retired GGOs
            for ggo in ggos_with_emissions:
                emissions.setdefault(m.begin, 0)
                emissions[m.begin] += \
                    EmissionValues(**ggo.emissions) * ggo.amount

            # Remaining emission from General mix
            if remaining_amount:
                mix = general_mix_emissions \
                    .get(m.sector, {}) \
                    .get(m.begin)

                if mix is not None:
                    emissions.setdefault(m.begin, 0)
                    emissions[m.begin] += \
                        EmissionValues(**mix.emissions) * remaining_amount

        return EcoDeclaration(
            emissions=emissions,
            consumed_amount=consumed_amount,
            resolution=EcoDeclarationResolution.hour,
        )

    def build_general_declaration(self, measurements, general_mix_emissions):
        """
        :param list[Measurement] measurements:
        :param dict[str, dict[datetime, EmissionData]] general_mix_emissions:
        :rtype: EcoDeclaration
        """

        # Emission in gram (mapped by begin)
        emissions = {}

        # Consumption in Wh (mapped by begin)
        consumed_amount = {}

        # Group measurements by their begin
        measurements_sorted_and_grouped = groupby(
            iterable=sorted(measurements, key=lambda m: m.begin),
            key=lambda m: m.begin,
        )

        for begin, measurements in measurements_sorted_and_grouped:
            begin_emissions = EmissionValues()
            begin_consumption = 0

            for sector in set(m.sector for m in measurements):
                mix = general_mix_emissions \
                    .get(sector, {}) \
                    .get(begin)

                if mix is not None:
                    begin_consumption += mix.amount
                    begin_emissions += \
                        EmissionValues(**mix.emissions) * mix.amount

            emissions[begin] = begin_emissions
            consumed_amount[begin] = begin_consumption

        return EcoDeclaration(
            emissions=emissions,
            consumed_amount=consumed_amount,
            resolution=EcoDeclarationResolution.hour,
        )

    def get_general_mix(self, meteringpoints, begin_from, begin_to):
        """
        :param list[MeteringPoint] meteringpoints:
        :param datetime begin_from:
        :param datetime begin_to:
        :rtype: dict[str, dict[datetime, EmissionData]]
        """
        general_mix = {}

        response = energytype_service.get_residual_mix(
            sector=list(set(m.sector for m in meteringpoints)),
            begin_from=begin_from,
            begin_to=begin_to,
        )

        for d in response.mix_emissions:
            general_mix.setdefault(d.sector, {})
            general_mix[d.sector][d.timestamp_utc] = d

        return general_mix

    def get_measurements(self, user, meteringpoints, begin_from, begin_to):
        """
        :param User user:
        :param list[MeteringPoint] meteringpoints:
        :param datetime begin_from:
        :param datetime begin_to:
        :rtype: list[Measurement]
        """
        request = GetMeasurementListRequest(
            offset=0,
            limit=99999,
            filters=MeasurementFilters(
                type=MeasurementType.CONSUMPTION,
                gsrn=[m.gsrn for m in meteringpoints],
                begin_range=DateTimeRange(
                    begin=begin_from,
                    end=begin_to,
                ),
            ),
        )

        response = datahub_service.get_measurements(
            token=user.access_token,
            request=request,
        )

        return response.measurements

    def get_retired_ggos(self, meteringpoints, session):
        """
        :param list[MeteringPoint] meteringpoints:
        :param sqlalchemy.orm.Session session:
        :rtype: dict[str, dict[datetime, list[Ggo]]]
        """
        retired_ggos = {}

        for ggo in self.fetch_retired_ggos_from_db(meteringpoints, session):
            retired_ggos \
                .setdefault(ggo.retire_gsrn, {}) \
                .setdefault(ggo.begin, []) \
                .append(ggo)

        return retired_ggos

    def fetch_retired_ggos_from_db(self, meteringpoints, session):
        """
        :param list[MeteringPoint] meteringpoints:
        :param sqlalchemy.orm.Session session:
        :rtype: list[Ggo]
        """
        return GgoQuery(session) \
            .is_retired_to_any_gsrn([m.gsrn for m in meteringpoints]) \
            .has_emissions() \
            .all()
