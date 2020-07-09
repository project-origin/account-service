from datetime import datetime

from origin.eco import EcoDeclaration, EmissionValues


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


def test__EcoDeclaration__total_consumed_amount():

    # Arrange
    uut = EcoDeclaration(
        emissions=emissions,
        consumed_amount=consumed_amount,
    )

    # Assert
    assert uut.total_consumed_amount == 10 + 20 + 30


def test__EcoDeclaration__total_emissions():

    # Arrange
    uut = EcoDeclaration(
        emissions=emissions,
        consumed_amount=consumed_amount,
    )

    # Assert
    assert uut.total_emissions == {
        'CO2': 100 + 300 + 500,
        'CH4': 200 + 400 + 600,
        'NOx': 700,
    }


def test__EcoDeclaration__emissions_per_wh():

    # Arrange
    uut = EcoDeclaration(
        emissions=emissions,
        consumed_amount=consumed_amount,
    )

    # Assert
    assert uut.emissions_per_wh == {
        begin1: {'CO2': 100/10, 'CH4': 200/10},
        begin2: {'CO2': 300/20, 'CH4': 400/20},
        begin3: {'CO2': 500/30, 'CH4': 600/30, 'NOx': 700/30},
    }


def test__EcoDeclaration__total_emissions_per_wh():

    # Arrange
    uut = EcoDeclaration(
        emissions=emissions,
        consumed_amount=consumed_amount,
    )

    # Assert
    assert uut.total_emissions_per_wh == {
        'CO2': (100 + 300 + 500) / (10 + 20 + 30),
        'CH4': (200 + 400 + 600) / (10 + 20 + 30),
        'NOx': 700 / (10 + 20 + 30),
    }
