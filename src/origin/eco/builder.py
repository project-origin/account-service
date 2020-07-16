from itertools import groupby
from datetime import datetime, timezone

from origin.ggo import GgoQuery, Ggo
from origin.common import EmissionValues, DateTimeRange
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
from .declaration import EcoDeclaration


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

        general_mix_emissions = self.get_general_mix(
            meteringpoints, begin_range)

        # Limit begin_range to where there is data in the general max,
        # so that no emission is calculated without general mix
        # ALSO ASSUME THERE ARE NO GAPS IN BEGINS!
        actual_begin_range = DateTimeRange(
            begin=min(general_mix_emissions.keys()),
            end=max(general_mix_emissions.keys()),
        )

        measurements = self.get_measurements(
            user, meteringpoints, actual_begin_range)

        retired_ggos = self.get_retired_ggos(
            meteringpoints, actual_begin_range, session)

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
        :param dict[datetime, dict[str, EmissionData]] general_mix_emissions:
        :rtype: EcoDeclaration
        """

        # Emission in gram (mapped by begin)
        emissions = {}

        # Consumption in Wh (mapped by begin)
        consumed_amount = {}

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

                technologies.setdefault(ggo.technology_label, 0)
                technologies[ggo.technology_label] += ggo.amount

            # Remaining emission from General mix
            # Assume there exists mix emissions for each
            # begin in the period, otherwise fail hard
            if remaining_amount:
                mix = general_mix_emissions[m.begin][m.sector]

                emissions[m.begin] += \
                    mix.emissions_per_wh * remaining_amount

                technologies += \
                    mix.technologies_share * remaining_amount

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
        :param dict[datetime, dict[str, EmissionData]] general_mix_emissions:
        :rtype: EcoDeclaration
        """

        # Emission in gram (mapped by begin)
        emissions = {}

        # Consumption in Wh (mapped by begin)
        consumed_amount = {}

        # Consumption in Wh (mapped by technology)
        technologies = EmissionValues()

        # Group measurements by their begin
        measurements_sorted_and_grouped = groupby(
            iterable=sorted(measurements, key=lambda m: m.begin),
            key=lambda m: m.begin,
        )

        for begin, measurements in measurements_sorted_and_grouped:
            unique_sectors_this_begin = set(m.sector for m in measurements)

            for sector in unique_sectors_this_begin:
                mix = general_mix_emissions[begin][sector]

                emissions.setdefault(begin, EmissionValues())
                emissions[begin] += mix.emissions

                consumed_amount.setdefault(begin, 0)
                consumed_amount[begin] += mix.amount

                technologies += mix.technologies

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
        :rtype: dict[datetime, dict[str, EmissionData]]
        """
        general_mix = {}

        response = energytype_service.get_residual_mix(
            sector=list(set(m.sector for m in meteringpoints)),
            begin_from=begin_range.begin.astimezone(timezone.utc),
            begin_to=begin_range.end.astimezone(timezone.utc),
        )

        for d in response.mix_emissions:
            general_mix.setdefault(d.timestamp_utc, {})
            general_mix[d.timestamp_utc][d.sector] = d

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
