from itertools import groupby
from datetime import datetime, timezone

from origin.ggo import GgoQuery, Ggo
from origin.common import DateTimeRange
from origin.auth import MeteringPoint, User
from origin.settings import UNKNOWN_TECHNOLOGY_LABEL
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

    def build_eco_declaration(self, user, meteringpoints, begin_range, session):
        """
        :param User user:
        :param list[MeteringPoint] meteringpoints:
        :param DateTimeRange begin_range:
        :param sqlalchemy.orm.Session session:
        :rtype: (EcoDeclaration, EcoDeclaration)
        :returns: A tuple of (individual declaration, general declaration)
        """
        assert len(meteringpoints) > 0

        # -- Dependencies ----------------------------------------------------

        measurements = self.get_measurements(
            user, meteringpoints, begin_range)

        retired_ggos = self.get_retired_ggos(
            meteringpoints, begin_range, session)

        general_mix_emissions = self.get_general_mix(
            meteringpoints, begin_range)

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
        consumed_amount = EmissionValues()

        # Consumption in Wh (mapped by technology)
        technologies = EmissionValues()

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

            # Set default (empty) emission values for this begin
            emissions.setdefault(m.begin, EmissionValues())

            # Emission from retired GGOs
            for ggo in ggos_with_emissions:
                emissions[m.begin] += \
                    EmissionValues(**ggo.emissions) * ggo.amount

                # TODO test this
                if ggo.technology is None:
                    technology = ggo.technology.technology
                else:
                    technology = UNKNOWN_TECHNOLOGY_LABEL

                technologies.setdefault(technology, 0)
                technologies[technology] += ggo.amount

            # Remaining emission from General mix
            if remaining_amount:
                mix = general_mix_emissions \
                    .get(m.sector, {}) \
                    .get(m.begin)

                if mix is not None:
                    # sum_of_parts = sum(p.share for p in mix.parts)
                    # assert sum_of_parts == 1, \
                    #     "Expected sum of parts to be 1, bus was %s" % sum_of_parts

                    emissions[m.begin] += \
                        EmissionValues(**mix.emissions) * remaining_amount

                    # TODO test only parts with share > 0 are included
                    for part in (p for p in mix.parts if p.share > 0):
                        technologies.setdefault(part.technology, 0)
                        technologies[part.technology] += remaining_amount * part.share

        return EcoDeclaration(
            emissions=emissions,
            consumed_amount=consumed_amount,
            technologies=technologies,
            resolution=EcoDeclarationResolution.hour,
            utc_offset=0,
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
        consumed_amount = EmissionValues()

        # Consumption in Wh (mapped by technology)
        technologies = EmissionValues()

        # Group measurements by their begin
        measurements_sorted_and_grouped = groupby(
            iterable=sorted(measurements, key=lambda m: m.begin),
            key=lambda m: m.begin,
        )

        for begin, measurements in measurements_sorted_and_grouped:
            begin_emissions = EmissionValues()
            begin_consumption = 0

            # TODO only include each sector ONCE

            for sector in set(m.sector for m in measurements):
                mix = general_mix_emissions \
                    .get(sector, {}) \
                    .get(begin)

                if mix is not None:
                    begin_consumption += mix.amount
                    begin_emissions += \
                        EmissionValues(**mix.emissions) * mix.amount

                    # TODO test only parts with share > 0 are included
                    for part in (p for p in mix.parts if p.share > 0):
                        technologies.setdefault(part.technology, 0)
                        technologies[part.technology] += mix.amount * part.share

            emissions[begin] = begin_emissions
            consumed_amount[begin] = begin_consumption

        return EcoDeclaration(
            emissions=emissions,
            consumed_amount=consumed_amount,
            technologies=technologies,
            resolution=EcoDeclarationResolution.hour,
            utc_offset=0,
        )

    def get_general_mix(self, meteringpoints, begin_range):
        """
        :param list[MeteringPoint] meteringpoints:
        :param DateTimeRange begin_range:
        :rtype: dict[str, dict[datetime, EmissionData]]
        """
        general_mix = {}

        response = energytype_service.get_residual_mix(
            sector=list(set(m.sector for m in meteringpoints)),
            begin_from=begin_range.begin.astimezone(timezone.utc),
            begin_to=begin_range.end.astimezone(timezone.utc),
        )

        for d in response.mix_emissions:
            general_mix.setdefault(d.sector, {})
            general_mix[d.sector][d.timestamp_utc] = d

        return general_mix

    def get_measurements(self, user, meteringpoints, begin_range):
        """
        :param User user:
        :param list[MeteringPoint] meteringpoints:
        :param DateTimeRange begin_range:
        :rtype: list[Measurement]
        """
        request = GetMeasurementListRequest(
            offset=0,
            limit=99999,
            filters=MeasurementFilters(
                type=MeasurementType.CONSUMPTION,
                gsrn=[m.gsrn for m in meteringpoints],
                begin_range=DateTimeRange(
                    begin=begin_range.begin.astimezone(timezone.utc),
                    end=begin_range.end.astimezone(timezone.utc),
                ),
            ),
        )

        response = datahub_service.get_measurements(
            token=user.access_token,
            request=request,
        )

        return response.measurements

    def get_retired_ggos(self, meteringpoints, begin_range, session):
        """
        :param list[MeteringPoint] meteringpoints:
        :param DateTimeRange begin_range:
        :param sqlalchemy.orm.Session session:
        :rtype: dict[str, dict[datetime, list[Ggo]]]
        """
        retired_ggos = self.fetch_retired_ggos_from_db(
            meteringpoints, begin_range, session)

        retired_ggos_mapped = {}

        for ggo in retired_ggos:
            retired_ggos_mapped \
                .setdefault(ggo.retire_gsrn, {}) \
                .setdefault(ggo.begin, []) \
                .append(ggo)

        return retired_ggos_mapped

    def fetch_retired_ggos_from_db(self, meteringpoints, begin_range, session):
        """
        :param list[MeteringPoint] meteringpoints:
        :param DateTimeRange begin_range:
        :param sqlalchemy.orm.Session session:
        :rtype: list[Ggo]
        """
        return GgoQuery(session) \
            .is_retired_to_any_gsrn([m.gsrn for m in meteringpoints]) \
            .begins_within(begin_range) \
            .has_emissions() \
            .all()
