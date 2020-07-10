from datetime import datetime

import pytest

from origin.eco import (
    EcoDeclaration,
    EmissionValues,
    EcoDeclarationResolution,
)


begin1 = datetime(2020, 1, 1, 1, 0)
begin2 = datetime(2020, 1, 1, 2, 0)
begin3 = datetime(2020, 1, 1, 3, 0)

emissions = {
    begin1: EmissionValues(**{'CO2': 100, 'CH4': 200}),
    begin2: EmissionValues(**{'CO2': 300, 'CH4': 400}),
    begin3: EmissionValues(**{'CO2': 500, 'CH4': 600, 'NOx': 700}),
}

consumed_amount = {
    begin1: 10,
    begin2: 20,
    begin3: 30,
}


def test__EcoDeclaration__total_consumed_amount__consumed_amount_exists__should_return_correct_number():

    # Arrange
    uut = EcoDeclaration(
        emissions=emissions,
        consumed_amount=consumed_amount,
        resolution=EcoDeclarationResolution.hour,
    )

    # Assert
    assert uut.total_consumed_amount == 10 + 20 + 30


def test__EcoDeclaration__total_consumed_amount__NO_consumed_amount_exists__should_return_zero():

    # Arrange
    uut = EcoDeclaration(
        emissions={},
        consumed_amount={},
        resolution=EcoDeclarationResolution.hour,
    )

    # Assert
    assert uut.total_consumed_amount == 0


def test__EcoDeclaration__total_emissions__emissions_exists__should_return_EmissionValues_with_correct_values():

    # Arrange
    uut = EcoDeclaration(
        emissions=emissions,
        consumed_amount=consumed_amount,
        resolution=EcoDeclarationResolution.hour,
    )

    # Assert
    assert isinstance(uut.total_emissions, EmissionValues)
    assert uut.total_emissions == {
        'CO2': 100 + 300 + 500,
        'CH4': 200 + 400 + 600,
        'NOx': 700,
    }


def test__EcoDeclaration__total_emissions__NO_emissions_exists__should_return_empty_EmissionValues():

    # Arrange
    uut = EcoDeclaration(
        emissions={},
        consumed_amount=consumed_amount,
        resolution=EcoDeclarationResolution.hour,
    )

    # Assert
    assert isinstance(uut.total_emissions, EmissionValues)
    assert uut.total_emissions == {}


def test__EcoDeclaration__emissions_per_wh__consumed_amount_exists__should_return_EmissionValues_with_correct_values():

    # Arrange
    uut = EcoDeclaration(
        emissions=emissions,
        consumed_amount=consumed_amount,
        resolution=EcoDeclarationResolution.hour,
    )

    # Assert
    assert isinstance(uut.emissions_per_wh, dict)
    assert all(isinstance(v, EmissionValues) for v in uut.emissions_per_wh.values())
    assert uut.emissions_per_wh == {
        begin1: {'CO2': 100/10, 'CH4': 200/10},
        begin2: {'CO2': 300/20, 'CH4': 400/20},
        begin3: {'CO2': 500/30, 'CH4': 600/30, 'NOx': 700/30},
    }


def test__EcoDeclaration__emissions_per_wh__NO_consumed_amount_exists__should_return_empty_EmissionValues():

    # Arrange
    uut = EcoDeclaration(
        emissions=emissions,
        consumed_amount={},
        resolution=EcoDeclarationResolution.hour,
    )

    # Assert
    assert isinstance(uut.emissions_per_wh, dict)
    assert all(isinstance(v, EmissionValues) for v in uut.emissions_per_wh.values())
    assert uut.emissions_per_wh == {
        begin1: {},
        begin2: {},
        begin3: {},
    }


def test__EcoDeclaration__total_emissions_per_wh__emissions_exists__should_return_EmissionValues_with_correct_values():

    # Arrange
    uut = EcoDeclaration(
        emissions=emissions,
        consumed_amount=consumed_amount,
        resolution=EcoDeclarationResolution.hour,
    )

    # Assert
    assert isinstance(uut.total_emissions_per_wh, EmissionValues)
    assert uut.total_emissions_per_wh == {
        'CO2': (100 + 300 + 500) / (10 + 20 + 30),
        'CH4': (200 + 400 + 600) / (10 + 20 + 30),
        'NOx': 700 / (10 + 20 + 30),
    }


def test__EcoDeclaration__total_emissions_per_wh__NO_emissions_exists__should_return_empty_EmissionValues():

    # Arrange
    uut = EcoDeclaration(
        emissions={},
        consumed_amount=consumed_amount,
        resolution=EcoDeclarationResolution.hour,
    )

    # Assert
    assert isinstance(uut.total_emissions_per_wh, EmissionValues)
    assert uut.total_emissions_per_wh == {}

# -- as_resolution() ---------------------------------------------------------


@pytest.mark.parametrize('current_resolution, new_resolution', (
        (EcoDeclarationResolution.all, EcoDeclarationResolution.year),
        (EcoDeclarationResolution.all, EcoDeclarationResolution.month),
        (EcoDeclarationResolution.all, EcoDeclarationResolution.day),
        (EcoDeclarationResolution.all, EcoDeclarationResolution.hour),
        (EcoDeclarationResolution.year, EcoDeclarationResolution.month),
        (EcoDeclarationResolution.year, EcoDeclarationResolution.day),
        (EcoDeclarationResolution.year, EcoDeclarationResolution.hour),
        (EcoDeclarationResolution.month, EcoDeclarationResolution.day),
        (EcoDeclarationResolution.month, EcoDeclarationResolution.hour),
        (EcoDeclarationResolution.day, EcoDeclarationResolution.hour),
))
def test__EcoDeclaration__as_resolution__resolution_is_higher_than_current__should_raise_ValueError(
        current_resolution, new_resolution):

    # Arrange
    uut = EcoDeclaration(
        emissions={},
        consumed_amount={},
        resolution=current_resolution,
    )

    # Assert
    with pytest.raises(ValueError):
        uut.as_resolution(new_resolution)
