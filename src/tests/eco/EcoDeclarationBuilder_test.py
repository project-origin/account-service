import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from origin.common import EmissionValues, DateTimeRange
from origin.ggo import Ggo
from origin.eco import EcoDeclarationBuilder, EcoDeclaration
from origin.services.datahub import (
    GetMeasurementListResponse,
    Measurement,
    MeasurementType,
)
from origin.services.energytypes import (
    GetMixEmissionsResponse,
    EmissionData,
    EmissionPart,
)


# -- build_eco_declaration() -------------------------------------------------


def test__EcoDeclarationBuilder__build_eco_declaration__no_meteringpoints_provided__should_raise_ValueError():

    # Arrange
    uut = EcoDeclarationBuilder()

    # Act + Assert
    with pytest.raises(ValueError):
        uut.build_eco_declaration(
            user=Mock(),
            meteringpoints=[],
            begin_range=Mock(),
            session=Mock(),
        )


def test__EcoDeclarationBuilder__build_eco_declaration__no_general_mix_exists__should_return_two_empty_declarations():

    # Arrange
    uut = EcoDeclarationBuilder()
    uut.get_general_mix = Mock(return_value={})

    # Act
    individual, general = uut.build_eco_declaration(
        user=Mock(),
        meteringpoints=[Mock(), Mock()],
        begin_range=Mock(),
        session=Mock(),
    )

    # Assert
    assert isinstance(individual, EcoDeclaration)
    assert individual.emissions == {}
    assert individual.consumed_amount == {}
    assert individual.technologies == {}

    assert isinstance(general, EcoDeclaration)
    assert general.emissions == {}
    assert general.consumed_amount == {}
    assert general.technologies == {}


def test__EcoDeclarationBuilder__build_eco_declaration__general_mix_only_exists_for_part_of_the_period__should_limit_declaration_to_period_with_general_mix():

    # Arrange
    begin1 = datetime(2020, 1, 1, 0, 0)
    begin2 = datetime(2020, 1, 2, 0, 0)
    begin3 = datetime(2020, 1, 3, 0, 0)
    begin4 = datetime(2020, 1, 4, 0, 0)

    uut = EcoDeclarationBuilder()
    uut.get_measurements = Mock()
    uut.get_retired_ggos = Mock()
    uut.build_general_declaration = Mock()
    uut.build_individual_declaration = Mock()
    uut.get_general_mix = Mock(return_value={
        begin2: None,
        begin3: None,
    })

    # Act
    uut.build_eco_declaration(
        user=Mock(),
        meteringpoints=[Mock(), Mock()],
        begin_range=DateTimeRange(begin=begin1, end=begin4),
        session=Mock(),
    )

    # Assert
    uut.get_measurements.assert_called_once()
    uut.get_retired_ggos.assert_called_once()

    get_measurements_call_kwargs = uut.get_measurements.call_args[1]
    get_retired_ggos_call_kwargs = uut.get_retired_ggos.call_args[1]

    assert get_measurements_call_kwargs['begin_range'].begin == begin2
    assert get_measurements_call_kwargs['begin_range'].end == begin3

    assert get_retired_ggos_call_kwargs['begin_range'].begin == begin2
    assert get_retired_ggos_call_kwargs['begin_range'].end == begin3


# -- Other -------------------------------------------------------------------


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

    # -- Arrange -------------------------------------------------------------

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

    measurements = [
        Mock(gsrn=gsrn1, sector='DK1', begin=begin1, amount=100),
        Mock(gsrn=gsrn1, sector='DK1', begin=begin2, amount=200),
        Mock(gsrn=gsrn1, sector='DK1', begin=begin3, amount=300),
        Mock(gsrn=gsrn1, sector='DK1', begin=begin4, amount=400),
        Mock(gsrn=gsrn1, sector='DK1', begin=begin5, amount=500),
        Mock(gsrn=gsrn1, sector='DK1', begin=begin6, amount=600),

        Mock(gsrn=gsrn2, sector='DK2', begin=begin3, amount=700),
        Mock(gsrn=gsrn2, sector='DK2', begin=begin4, amount=800),
        Mock(gsrn=gsrn2, sector='DK2', begin=begin6, amount=900),

        # No Retired GGOs exists for GSRN3
        Mock(gsrn=gsrn3, sector='DK2', begin=begin6, amount=1000),
    ]

    retired_ggos = {
        gsrn1: {
            begin1: [Mock(amount=100, technology_label='Coal', emissions={'CO2': 1, 'CH4': 2})],
            begin2: [Mock(amount=25, technology_label='Coal', emissions={'CO2': 3, 'CH4': 4}), Mock(amount=50, emissions=None)],
            begin3: [Mock(amount=300, technology_label='Coal', emissions={'CO2': 5, 'CH4': 6})],
            begin4: [Mock(amount=60, technology_label='Coal', emissions={'CO2': 7, 'CH4': 8})],
        },
        gsrn2: {
            begin3: [Mock(amount=700, technology_label='Coal', emissions={'CO2': 9, 'CH4': 10})],
            begin4: [Mock(amount=50, technology_label='Coal', emissions={'CO2': 11, 'CH4': 12}), Mock(amount=50, emissions=None)],
        },
    }

    general_mix_emissions = {
        begin1: {
            'DK1': Mock(
                emissions_per_wh=EmissionValues(CO2=13, CH4=14),
                technologies_share=EmissionValues(Solar=0.5, Wind=0.5),
            ),
        },
        begin2: {
            'DK1': Mock(
                emissions_per_wh=EmissionValues(CO2=15, CH4=16),
                technologies_share=EmissionValues(Solar=0.5, Wind=0.5),
            ),
        },
        begin3: {
            'DK1': Mock(
                emissions_per_wh=EmissionValues(CO2=17, CH4=18),
                technologies_share=EmissionValues(Solar=0.5, Wind=0.5),
            ),
            'DK2': Mock(
                emissions_per_wh=EmissionValues(CO2=25, CH4=26),
                technologies_share=EmissionValues(Solar=0.5, Wind=0.5),
            ),
        },
        begin4: {
            'DK1': Mock(
                emissions_per_wh=EmissionValues(CO2=19, CH4=20),
                technologies_share=EmissionValues(Solar=0.5, Wind=0.5),
            ),
            'DK2': Mock(
                emissions_per_wh=EmissionValues(CO2=27, CH4=28),
                technologies_share=EmissionValues(Solar=0.5, Wind=0.5),
            ),
        },
        begin5: {
            'DK1': Mock(
                emissions_per_wh=EmissionValues(CO2=21, CH4=22),
                technologies_share=EmissionValues(Solar=0.5, Wind=0.5),
            ),
        },
        begin6: {
            'DK1': Mock(
                emissions_per_wh=EmissionValues(CO2=23, CH4=24),
                technologies_share=EmissionValues(Solar=0.5, Wind=0.5),
            ),
            'DK2': Mock(
                emissions_per_wh=EmissionValues(CO2=29, CH4=30),
                technologies_share=EmissionValues(Solar=0.5, Wind=0.5),
            ),
        },
    }

    # -- Act -----------------------------------------------------------------

    declaration = uut.build_individual_declaration(
        measurements=measurements,
        retired_ggos=retired_ggos,
        general_mix_emissions=general_mix_emissions,
    )

    # -- Assert --------------------------------------------------------------

    assert declaration.consumed_amount == {
        begin1: 100,
        begin2: 200,
        begin3: 300 + 700,
        begin4: 400 + 800,
        begin5: 500,
        begin6: 600 + 900 + 1000,
    }

    # TODO Assert declaration.technologies

    assert declaration.emissions[begin1] == {
        'CO2': 100*1,
        'CH4': 100*2,
    }

    assert declaration.emissions[begin2] == {
        'CO2': 25*3 + (200-25)*15,
        'CH4': 25*4 + (200-25)*16,
    }

    assert declaration.emissions[begin3] == {
        'CO2': 300*5 + 700*9,
        'CH4': 300*6 + 700*10,
    }

    assert declaration.emissions[begin4] == {
        'CO2': 60*7 + (400-60)*19 + 50*11 + (800-50)*27,
        'CH4': 60*8 + (400-60)*20 + 50*12 + (800-50)*28,
    }

    assert declaration.emissions[begin5] == {
        'CO2': 500*21,
        'CH4': 500*22,
    }

    assert declaration.emissions[begin6] == {
        'CO2': 600*23 + 900*29 + 1000*29,
        'CH4': 600*24 + 900*30 + 1000*30,
    }


def test__EcoDeclarationBuilder__build_general_declaration():

    # -- Arrange -------------------------------------------------------------

    uut = EcoDeclarationBuilder()

    begin1 = datetime(2020, 1, 1, 1, 0)
    begin2 = datetime(2020, 1, 1, 2, 0)
    begin3 = datetime(2020, 1, 1, 3, 0)

    measurements = [
        Mock(sector='DK1', begin=begin1),
        Mock(sector='DK1', begin=begin2),
        Mock(sector='DK1', begin=begin3),

        # Two measurements in DK2 at begin2, only one of them should count
        Mock(sector='DK2', begin=begin1),
        Mock(sector='DK2', begin=begin2),
        Mock(sector='DK2', begin=begin2),
    ]

    general_mix_emissions = {
        begin1: {
            'DK1': Mock(
                amount=110,
                emissions=EmissionValues(CO2=111, CH4=222),
                technologies=EmissionValues(Solar=35, Wind=75),
            ),
            'DK2': Mock(
                amount=220,
                emissions=EmissionValues(CO2=333, CH4=444),
                technologies=EmissionValues(Solar=130, Wind=90),
            ),
        },
        begin2: {
            'DK1': Mock(
                amount=330,
                emissions=EmissionValues(CO2=555, CH4=666),
                technologies=EmissionValues(Solar=91, Wind=239),
            ),
            'DK2': Mock(
                amount=440,
                emissions=EmissionValues(CO2=777, CH4=888),
                technologies=EmissionValues(Solar=250, Wind=190),
            ),
        },
        begin3: {
            'DK1': Mock(
                amount=500,
                emissions=EmissionValues(CO2=999, CH4=101010),
                technologies=EmissionValues(Solar=490, Wind=10),
            ),
        },
    }

    # -- Act -----------------------------------------------------------------

    declaration = uut.build_general_declaration(
        measurements=measurements,
        general_mix_emissions=general_mix_emissions,
    )

    # -- Assert --------------------------------------------------------------

    assert declaration.consumed_amount == {
        begin1: 110 + 220,
        begin2: 330 + 440,
        begin3: 500,
    }

    assert declaration.technologies == {
        'Solar': 35 + 130 + 91 + 250 + 490,
        'Wind': 75 + 90 + 239 + 190 + 10,
    }

    assert declaration.emissions[begin1] == {
        'CO2': 111 + 333,
        'CH4': 222 + 444,
    }

    assert declaration.emissions[begin2] == {
        'CO2': 555 + 777,
        'CH4': 666 + 888,
    }

    assert declaration.emissions[begin3] == {
        'CO2': 999,
        'CH4': 101010,
    }


@patch('origin.eco.builder.datahub_service')
@patch('origin.eco.builder.energytype_service')
def test__EcoDeclarationBuilder__integration(energytype_service_mock, datahub_service_mock):

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

    begin0 = datetime(2020, 1, 1, 1, 0, tzinfo=timezone.utc)
    begin1 = datetime(2020, 1, 1, 1, 0, tzinfo=timezone.utc)
    begin2 = datetime(2020, 1, 1, 2, 0, tzinfo=timezone.utc)
    begin3 = datetime(2020, 1, 1, 3, 0, tzinfo=timezone.utc)
    begin4 = datetime(2020, 1, 1, 4, 0, tzinfo=timezone.utc)

    # datahub_service.get_measurements()
    datahub_service_mock.get_measurements.return_value = GetMeasurementListResponse(
        success=True,
        total=9,
        measurements=[
            Measurement(gsrn=gsrn1, sector='DK1', begin=begin1, amount=100000, end=None, address=None, type=None),
            Measurement(gsrn=gsrn1, sector='DK1', begin=begin2, amount=200000, end=None, address=None, type=None),
            Measurement(gsrn=gsrn1, sector='DK1', begin=begin3, amount=300000, end=None, address=None, type=None),
            Measurement(gsrn=gsrn1, sector='DK1', begin=begin4, amount=400000, end=None, address=None, type=None),

            Measurement(gsrn=gsrn2, sector='DK2', begin=begin3, amount=700000, end=None, address=None, type=None),
            Measurement(gsrn=gsrn2, sector='DK2', begin=begin4, amount=800000, end=None, address=None, type=None),

            # No Retired GGOs exists for GSRN3
            # Two measurements in DK2 at begin6, only one of them should count
            Measurement(gsrn=gsrn3, sector='DK2', begin=begin4, amount=1000000, end=None, address=None, type=None),
        ]
    )

    # energytype_service.get_residual_mix()
    energytype_service_mock.get_residual_mix.return_value = GetMixEmissionsResponse(
        success=True,
        mix_emissions=[
            # DK1
            EmissionData(sector='DK1', timestamp_utc=begin1, parts=[
                EmissionPart(technology='Solar', amount=111, emissions=EmissionValues(CO2=50, CH4=51)),
                EmissionPart(technology='Wind', amount=222, emissions=EmissionValues(CO2=52, CH4=53)),
            ]),
            EmissionData(sector='DK1', timestamp_utc=begin2, parts=[
                EmissionPart(technology='Solar', amount=333, emissions=EmissionValues(CO2=54, CH4=55)),
                EmissionPart(technology='Wind', amount=444, emissions=EmissionValues(CO2=56, CH4=57)),
            ]),
            EmissionData(sector='DK1', timestamp_utc=begin3, parts=[
                EmissionPart(technology='Solar', amount=555, emissions=EmissionValues(CO2=58, CH4=59)),
                EmissionPart(technology='Wind', amount=666, emissions=EmissionValues(CO2=60, CH4=61)),
            ]),
            EmissionData(sector='DK1', timestamp_utc=begin4, parts=[
                EmissionPart(technology='Solar', amount=777, emissions=EmissionValues(CO2=62, CH4=63)),
                EmissionPart(technology='Wind', amount=888, emissions=EmissionValues(CO2=64, CH4=65)),
            ]),

            # DK2
            EmissionData(sector='DK2', timestamp_utc=begin3, parts=[
                EmissionPart(technology='Solar', amount=131313, emissions=EmissionValues(CO2=74, CH4=75)),
                EmissionPart(technology='Wind', amount=141414, emissions=EmissionValues(CO2=76, CH4=77)),
            ]),
            EmissionData(sector='DK2', timestamp_utc=begin4, parts=[
                EmissionPart(technology='Solar', amount=151515, emissions=EmissionValues(CO2=78, CH4=79)),
                EmissionPart(technology='Wind', amount=161616, emissions=EmissionValues(CO2=80, CH4=81)),
            ]),
        ]
    )

    # uut.fetch_retired_ggos_from_db()
    uut.fetch_retired_ggos_from_db = Mock(return_value=[
        # GSRN1
        Ggo(retire_gsrn=gsrn1, begin=begin1, amount=100000, emissions={'CO2': 1, 'CH4': 2}, technology=Mock(technology='Nuclear')),
        Ggo(retire_gsrn=gsrn1, begin=begin2, amount=2222, emissions={'CO2': 3, 'CH4': 4}, technology=Mock(technology='Oil')),
        Ggo(retire_gsrn=gsrn1, begin=begin2, amount=3333, emissions=None, technology=Mock(technology='Waste')),  # No emissions - is ignored
        Ggo(retire_gsrn=gsrn1, begin=begin3, amount=4444, emissions={'CO2': 5, 'CH4': 6}, technology=Mock(technology='Hydro')),
        Ggo(retire_gsrn=gsrn1, begin=begin4, amount=5555, emissions={'CO2': 7, 'CH4': 8}, technology=Mock(technology='Coal')),

        # GSRN2
        Ggo(retire_gsrn=gsrn2, begin=begin3, amount=6666, emissions={'CO2': 9, 'CH4': 10}, technology=Mock(technology='Biomass')),
        Ggo(retire_gsrn=gsrn2, begin=begin4, amount=7777, emissions={'CO2': 11, 'CH4': 12}, technology=Mock(technology='Naturalgas')),
        Ggo(retire_gsrn=gsrn2, begin=begin4, amount=8888, emissions=None, technology=Mock(technology='Biogas')),  # No emissions - is ignored
    ])

    # -- Act -----------------------------------------------------------------

    individual, general = uut.build_eco_declaration(
        user=user,
        meteringpoints=meteringpoints,
        begin_range=DateTimeRange(begin=begin0, end=begin4),
        session=Mock(),
    )

    # -- Assert --------------------------------------------------------------

    # Individual declaration

    assert individual.consumed_amount == {
        begin1: 100000,
        begin2: 200000,
        begin3: 300000 + 700000,
        begin4: 400000 + 800000 + 1000000,
    }

    # TODO assert technologies

    assert individual.emissions[begin1] == {
        'CO2': 100000*1,
        'CH4': 100000*2,
    }

    assert individual.emissions[begin2] == {
        'CO2': 2222*3 + (200000-2222)*((54+56)/(333+444)),
        'CH4': 2222*4 + (200000-2222)*((55+57)/(333+444)),
    }

    assert individual.emissions[begin3] == {
        'CO2': 4444*5 + (300000-4444)*((58+60)/(555+666))
               + 6666*9 + (700000-6666)*((74+76)/(131313+141414)),

        'CH4': 4444*6 + (300000-4444)*((59+61)/(555+666))
               + 6666*10 + (700000-6666)*((75+77)/(131313+141414)),
    }

    assert individual.emissions[begin4] == {
        'CO2': 5555*7 + (400000-5555)*((62+64)/(777+888))
               + 7777*11 + (800000-7777)*((78+80)/(151515+161616))
               + 1000000*((78+80)/(151515+161616)),

        'CH4': 5555*8 + (400000-5555)*((63+65)/(777+888))
               + 7777*12 + (800000-7777)*((79+81)/(151515+161616))
               + 1000000*((79+81)/(151515+161616)),
    }

    # General declaration

    assert general.consumed_amount == {
        begin1: 111 + 222,
        begin2: 333 + 444,
        begin3: 555 + 666 + 131313 + 141414,
        begin4: 777 + 888 + 151515 + 161616,
    }

    # TODO assert technologies

    assert general.emissions[begin1] == {
        'CO2': 50+52,
        'CH4': 51+53,
    }

    assert general.emissions[begin2] == {
        'CO2': 54+56,
        'CH4': 55+57,
    }

    assert general.emissions[begin3] == {
        'CO2': 58+60 + 74+76,
        'CH4': 59+61 + 75+77,
    }

    assert general.emissions[begin4] == {
        'CO2': 62+64 + 78+80,
        'CH4': 63+65 + 79+81,
    }

    # Correct call parameters to datahub_service_mock.get_measurements()

    datahub_service_mock.get_measurements.assert_called_once()

    get_measurements_call_args = datahub_service_mock.get_measurements.call_args[1]

    assert get_measurements_call_args['token'] is user.access_token
    assert get_measurements_call_args['request'].filters.type is MeasurementType.CONSUMPTION
    assert get_measurements_call_args['request'].filters.gsrn == [gsrn1, gsrn2, gsrn3]
    assert get_measurements_call_args['request'].filters.begin_range.begin == begin1
    assert get_measurements_call_args['request'].filters.begin_range.end == begin4

    # Correct call parameters to energytype_service.get_residual_mix()

    energytype_service_mock.get_residual_mix.assert_called_once()

    get_residual_mix_call_args = energytype_service_mock.get_residual_mix.call_args[1]

    assert sorted(get_residual_mix_call_args['sector']) == ['DK1', 'DK2']
    assert get_residual_mix_call_args['begin_from'] == begin1
    assert get_residual_mix_call_args['begin_to'] == begin4
