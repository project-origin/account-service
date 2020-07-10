from datetime import datetime
from unittest.mock import Mock, patch

from origin.ggo import Ggo
from origin.eco import EcoDeclarationBuilder
from origin.services.datahub import (
    GetMeasurementListResponse,
    Measurement,
    MeasurementType,
)
from origin.services.energytypes import (
    GetMixEmissionsResponse,
    EmissionData,
)


def test__EcoDeclarationBuilder__build_individual_declaration():
    """
    begin1: One measurement with 100% of emission from retired GGO

    begin2: One measurement with 50% of emission from retired GGO
            and 50% emission from general mix emissions

    begin3: Two measurements with 100% of emission from retired GGOs

    begin4: Two measurements with 50% of emission from retired GGOs
            and 50% emission from general mix emissions

    begin5: One measurement with 100% of emission from general mix emissions

    begin6: Two measurements with 100% of emission from general mix emissions
    """

    # Arrange
    uut = EcoDeclarationBuilder()

    gsrn1 = 'GSRN1'
    gsrn2 = 'GSRN2'
    gsrn3 = 'GSRN3'

    begin1 = datetime(2020, 1, 1, 1, 0)
    begin2 = datetime(2020, 1, 1, 2, 0)
    begin3 = datetime(2020, 1, 1, 3, 0)
    begin4 = datetime(2020, 1, 1, 4, 0)
    begin5 = datetime(2020, 1, 1, 5, 0)
    begin6 = datetime(2020, 1, 1, 6, 0)
    begin7 = datetime(2020, 1, 1, 7, 0)

    measurements = [
        Mock(gsrn=gsrn1, sector='DK1', begin=begin1, amount=100),
        Mock(gsrn=gsrn1, sector='DK1', begin=begin2, amount=100),
        Mock(gsrn=gsrn1, sector='DK1', begin=begin3, amount=100),
        Mock(gsrn=gsrn1, sector='DK1', begin=begin4, amount=100),
        Mock(gsrn=gsrn1, sector='DK1', begin=begin5, amount=100),
        Mock(gsrn=gsrn1, sector='DK1', begin=begin6, amount=100),

        Mock(gsrn=gsrn2, sector='DK2', begin=begin3, amount=100),
        Mock(gsrn=gsrn2, sector='DK2', begin=begin4, amount=100),
        Mock(gsrn=gsrn2, sector='DK2', begin=begin6, amount=100),

        # No Retired GGOs exists for GSRN3
        # No General Mix Emissions exists for begin7
        Mock(gsrn=gsrn3, sector='DK2', begin=begin7, amount=100),
    ]

    retired_ggos = {
        gsrn1: {
            begin1: [Mock(amount=100, emissions={'CO2': 1, 'CH4': 2})],
            begin2: [Mock(amount=50, emissions={'CO2': 3, 'CH4': 4}), Mock(amount=50, emissions=None)],
            begin3: [Mock(amount=100, emissions={'CO2': 5, 'CH4': 6})],
            begin4: [Mock(amount=50, emissions={'CO2': 7, 'CH4': 8})],
        },
        gsrn2: {
            begin3: [Mock(amount=100, emissions={'CO2': 9, 'CH4': 10})],
            begin4: [Mock(amount=50, emissions={'CO2': 11, 'CH4': 12}), Mock(amount=50, emissions=None)],
        },
    }

    general_mix_emissions = {
        'DK1': {
            begin1: Mock(emissions={'CO2': 13, 'CH4': 14}),
            begin2: Mock(emissions={'CO2': 15, 'CH4': 16}),
            begin3: Mock(emissions={'CO2': 17, 'CH4': 18}),
            begin4: Mock(emissions={'CO2': 19, 'CH4': 20}),
            begin5: Mock(emissions={'CO2': 21, 'CH4': 22}),
            begin6: Mock(emissions={'CO2': 23, 'CH4': 24}),
        },
        'DK2': {
            begin3: Mock(emissions={'CO2': 29, 'CH4': 30}),
            begin4: Mock(emissions={'CO2': 31, 'CH4': 32}),
            begin6: Mock(emissions={'CO2': 35, 'CH4': 36}),
        },
    }

    # Act
    declaration = uut.build_individual_declaration(
        measurements=measurements,
        retired_ggos=retired_ggos,
        general_mix_emissions=general_mix_emissions,
    )

    # Assert
    assert declaration.consumed_amount == {
        begin1: 100,
        begin2: 100,
        begin3: 100 + 100,
        begin4: 100 + 100,
        begin5: 100,
        begin6: 100 + 100,
        begin7: 100,
    }

    assert declaration.emissions[begin1] == {
        'CO2': 100*1,
        'CH4': 100*2,
    }

    assert declaration.emissions[begin2] == {
        'CO2': 50*3 + 50*15,
        'CH4': 50*4 + 50*16,
    }

    assert declaration.emissions[begin3] == {
        'CO2': 100*5 + 100*9,
        'CH4': 100*6 + 100*10,
    }

    assert declaration.emissions[begin4] == {
        'CO2': 50*7 + 50*11 + 50*19 + 50*31,
        'CH4': 50*8 + 50*12 + 50*20 + 50*32,
    }

    assert declaration.emissions[begin5] == {
        'CO2': 100*21,
        'CH4': 100*22,
    }

    assert declaration.emissions[begin6] == {
        'CO2': 100*23 + 100*35,
        'CH4': 100*24 + 100*36,
    }

    assert declaration.emissions[begin7] == {}


def test__EcoDeclarationBuilder__build_general_declaration():

    # Arrange
    uut = EcoDeclarationBuilder()

    begin1 = datetime(2020, 1, 1, 1, 0)
    begin2 = datetime(2020, 1, 1, 2, 0)
    begin3 = datetime(2020, 1, 1, 3, 0)
    begin4 = datetime(2020, 1, 1, 3, 0)

    measurements = [
        Mock(sector='DK1', begin=begin1),
        Mock(sector='DK1', begin=begin2),
        Mock(sector='DK1', begin=begin3),

        Mock(sector='DK2', begin=begin1),
        Mock(sector='DK2', begin=begin2),
        Mock(sector='DK2', begin=begin2),

        # No General Mix Emissions exists for begin4
        Mock(sector='DK2', begin=begin4),
    ]

    general_mix_emissions = {
        'DK1': {
            begin1: Mock(amount=100, emissions={'CO2': 1, 'CH4': 2}),
            begin2: Mock(amount=200, emissions={'CO2': 3, 'CH4': 4}),
            begin3: Mock(amount=300, emissions={'CO2': 5, 'CH4': 6}),
        },
        'DK2': {
            begin1: Mock(amount=400, emissions={'CO2': 7, 'CH4': 8}),
            begin2: Mock(amount=500, emissions={'CO2': 9, 'CH4': 10}),
        },
    }

    # Act
    declaration = uut.build_general_declaration(
        measurements=measurements,
        general_mix_emissions=general_mix_emissions,
    )

    # Assert
    assert declaration.consumed_amount == {
        begin1: 500,
        begin2: 700,
        begin3: 300,
    }

    assert declaration.emissions[begin1] == {
        'CO2': 100*1 + 400*7,
        'CH4': 100*2 + 400*8,
    }

    assert declaration.emissions[begin2] == {
        'CO2': 200*3 + 500*9,
        'CH4': 200*4 + 500*10,
    }

    assert declaration.emissions[begin3] == {
        'CO2': 300*5,
        'CH4': 300*6,
    }


@patch('origin.eco.builder.datahub_service')
@patch('origin.eco.builder.energytype_service')
def test__EcoDeclarationBuilder__build_eco_declaration(energytype_service_mock, datahub_service_mock):

    # -- Arrange -------------------------------------------------------------

    uut = EcoDeclarationBuilder()

    user = Mock()
    gsrn1 = 'GSRN1'
    gsrn2 = 'GSRN2'
    gsrn3 = 'GSRN3'
    meteringpoints = [
        Mock(gsrn=gsrn1, sector='DK1'),
        Mock(gsrn=gsrn2, sector='DK2'),
        Mock(gsrn=gsrn3, sector='DK2'),
    ]

    begin1 = datetime(2020, 1, 1, 1, 0)
    begin2 = datetime(2020, 1, 1, 2, 0)
    begin3 = datetime(2020, 1, 1, 3, 0)
    begin4 = datetime(2020, 1, 1, 4, 0)
    begin5 = datetime(2020, 1, 1, 5, 0)
    begin6 = datetime(2020, 1, 1, 6, 0)
    begin7 = datetime(2020, 1, 1, 7, 0)

    # datahub_service.get_measurements()
    datahub_service_mock.get_measurements.return_value = GetMeasurementListResponse(
        success=True,
        total=9,
        measurements=[
            Measurement(gsrn=gsrn1, sector='DK1', begin=begin1, amount=100, end=None, address=None, type=None),
            Measurement(gsrn=gsrn1, sector='DK1', begin=begin2, amount=100, end=None, address=None, type=None),
            Measurement(gsrn=gsrn1, sector='DK1', begin=begin3, amount=100, end=None, address=None, type=None),
            Measurement(gsrn=gsrn1, sector='DK1', begin=begin4, amount=100, end=None, address=None, type=None),
            Measurement(gsrn=gsrn1, sector='DK1', begin=begin5, amount=100, end=None, address=None, type=None),
            Measurement(gsrn=gsrn1, sector='DK1', begin=begin6, amount=100, end=None, address=None, type=None),

            Measurement(gsrn=gsrn2, sector='DK2', begin=begin3, amount=100, end=None, address=None, type=None),
            Measurement(gsrn=gsrn2, sector='DK2', begin=begin4, amount=100, end=None, address=None, type=None),
            Measurement(gsrn=gsrn2, sector='DK2', begin=begin6, amount=100, end=None, address=None, type=None),

            # No Retired GGOs exists for GSRN3
            # No General Mix Emissions exists for begin7
            Measurement(gsrn=gsrn3, sector='DK2', begin=begin7, amount=100, end=None, address=None, type=None),
        ]
    )

    # energytype_service.get_residual_mix()
    energytype_service_mock.get_residual_mix.return_value = GetMixEmissionsResponse(
        success=True,
        mix_emissions=[
            EmissionData(sector='DK1', timestamp_utc=begin1, amount=100, emissions={'CO2': 13, 'CH4': 14}, parts=None),
            EmissionData(sector='DK1', timestamp_utc=begin2, amount=200, emissions={'CO2': 15, 'CH4': 16}, parts=None),
            EmissionData(sector='DK1', timestamp_utc=begin3, amount=300, emissions={'CO2': 17, 'CH4': 18}, parts=None),
            EmissionData(sector='DK1', timestamp_utc=begin4, amount=400, emissions={'CO2': 19, 'CH4': 20}, parts=None),
            EmissionData(sector='DK1', timestamp_utc=begin5, amount=500, emissions={'CO2': 21, 'CH4': 22}, parts=None),
            EmissionData(sector='DK1', timestamp_utc=begin6, amount=600, emissions={'CO2': 23, 'CH4': 24}, parts=None),
            EmissionData(sector='DK2', timestamp_utc=begin3, amount=700, emissions={'CO2': 29, 'CH4': 30}, parts=None),
            EmissionData(sector='DK2', timestamp_utc=begin4, amount=800, emissions={'CO2': 31, 'CH4': 32}, parts=None),
            EmissionData(sector='DK2', timestamp_utc=begin6, amount=900, emissions={'CO2': 35, 'CH4': 36}, parts=None),
        ]
    )

    # uut.fetch_retired_ggos_from_db()
    uut.fetch_retired_ggos_from_db = Mock(return_value=[
        Ggo(retire_gsrn=gsrn1, begin=begin1, amount=100, emissions={'CO2': 1, 'CH4': 2}),
        Ggo(retire_gsrn=gsrn1, begin=begin2, amount=50, emissions={'CO2': 3, 'CH4': 4}),
        Ggo(retire_gsrn=gsrn1, begin=begin2, amount=50, emissions=None),
        Ggo(retire_gsrn=gsrn1, begin=begin3, amount=100, emissions={'CO2': 5, 'CH4': 6}),
        Ggo(retire_gsrn=gsrn1, begin=begin4, amount=50, emissions={'CO2': 7, 'CH4': 8}),
        Ggo(retire_gsrn=gsrn2, begin=begin3, amount=100, emissions={'CO2': 9, 'CH4': 10}),
        Ggo(retire_gsrn=gsrn2, begin=begin4, amount=50, emissions={'CO2': 11, 'CH4': 12}),
        Ggo(retire_gsrn=gsrn2, begin=begin4, amount=50, emissions=None),
    ])

    # -- Act -----------------------------------------------------------------

    individual, general = uut.build_eco_declaration(
        user=user,
        meteringpoints=meteringpoints,
        begin_from=begin1,
        begin_to=begin6,
        session=Mock(),
    )

    # -- Assert --------------------------------------------------------------

    # Individual declaration

    assert individual.consumed_amount == {
        begin1: 100,
        begin2: 100,
        begin3: 100 + 100,
        begin4: 100 + 100,
        begin5: 100,
        begin6: 100 + 100,
        begin7: 100,
    }

    assert individual.emissions[begin1] == {
        'CO2': 100*1,
        'CH4': 100*2,
    }

    assert individual.emissions[begin2] == {
        'CO2': 50*3 + 50*15,
        'CH4': 50*4 + 50*16,
    }

    assert individual.emissions[begin3] == {
        'CO2': 100*5 + 100*9,
        'CH4': 100*6 + 100*10,
    }

    assert individual.emissions[begin4] == {
        'CO2': 50*7 + 50*11 + 50*19 + 50*31,
        'CH4': 50*8 + 50*12 + 50*20 + 50*32,
    }

    assert individual.emissions[begin5] == {
        'CO2': 100*21,
        'CH4': 100*22,
    }

    assert individual.emissions[begin6] == {
        'CO2': 100*23 + 100*35,
        'CH4': 100*24 + 100*36,
    }

    assert individual.emissions[begin7] == {}

    # General declaration

    assert general.consumed_amount == {
        begin1: 100,
        begin2: 200,
        begin3: 300 + 700,
        begin4: 400 + 800,
        begin5: 500,
        begin6: 600 + 900,
        begin7: 0,
    }

    assert general.emissions[begin1] == {
        'CO2': 100*13,
        'CH4': 100*14,
    }

    assert general.emissions[begin2] == {
        'CO2': 200*15,
        'CH4': 200*16,
    }

    assert general.emissions[begin3] == {
        'CO2': 300*17 + 700*29,
        'CH4': 300*18 + 700*30,
    }

    assert general.emissions[begin4] == {
        'CO2': 400*19 + 800*31,
        'CH4': 400*20 + 800*32,
    }

    assert general.emissions[begin5] == {
        'CO2': 500*21,
        'CH4': 500*22,
    }

    assert general.emissions[begin6] == {
        'CO2': 600*23 + 900*35,
        'CH4': 600*24 + 900*36,
    }

    assert general.emissions[begin7] == {}

    # Correct call parameters to datahub_service_mock.get_measurements()

    datahub_service_mock.get_measurements.assert_called_once()

    get_measurements_call_args = datahub_service_mock.get_measurements.call_args[1]

    assert get_measurements_call_args['token'] is user.access_token
    assert get_measurements_call_args['request'].filters.type is MeasurementType.CONSUMPTION
    assert get_measurements_call_args['request'].filters.gsrn == [gsrn1, gsrn2, gsrn3]
    assert get_measurements_call_args['request'].filters.begin_range.begin == begin1
    assert get_measurements_call_args['request'].filters.begin_range.end == begin6

    # Correct call parameters to energytype_service.get_residual_mix()

    energytype_service_mock.get_residual_mix.assert_called_once()

    get_residual_mix_call_args = energytype_service_mock.get_residual_mix.call_args[1]

    assert sorted(get_residual_mix_call_args['sector']) == ['DK1', 'DK2']
    assert get_residual_mix_call_args['begin_from'] == begin1
    assert get_residual_mix_call_args['begin_to'] == begin6
