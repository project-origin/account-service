import pytest
from datetime import datetime

from origin.common import EmissionValues
from origin.eco import EcoDeclaration, EcoDeclarationResolution


begin1 = datetime(2020, 1, 1, 1, 0)
begin2 = datetime(2020, 1, 1, 2, 0)
begin3 = datetime(2020, 1, 1, 3, 0)


# -- Constructor -------------------------------------------------------------


def test__EcoDeclaration__constructor__emissions_values_are_not_all_of_type_EmissionValues__should_raise_ValueError():
    with pytest.raises(ValueError):
        EcoDeclaration(
            emissions={
                begin1: EmissionValues(),
                begin2: {},  # Should be EmissionValues instance
            },
            consumed_amount={
                begin1: 100,
                begin2: 100,
            },
            technologies=EmissionValues(
                CO2=100,
                NOx=100,
            ),
            resolution=EcoDeclarationResolution.hour,
            utc_offset=0,
        )


def test__EcoDeclaration__constructor__technologies_values_are_not_all_of_type_EmissionValues__should_raise_ValueError():
    with pytest.raises(ValueError):
        EcoDeclaration(
            emissions={
                begin1: EmissionValues(),
                begin2: EmissionValues(),
            },
            consumed_amount={
                begin1: 100,
                begin2: 100,
            },
            technologies=dict(  # Should be EmissionValues instance
                CO2=100,
                NOx=100,
            ),
            resolution=EcoDeclarationResolution.hour,
            utc_offset=0,
        )


def test__EcoDeclaration__constructor__consumed_amount_is_not_of_type_dict__should_raise_ValueError():
    with pytest.raises(ValueError):
        EcoDeclaration(
            emissions={
                begin1: EmissionValues(),
                begin2: EmissionValues(),
            },
            consumed_amount=123,  # Should be dict
            technologies=EmissionValues(
                CO2=100,
                NOx=100,
            ),
            resolution=EcoDeclarationResolution.hour,
            utc_offset=0,
        )


def test__EcoDeclaration__constructor__sum_of_consumed_amount_is_not_equal_to_sum_of_technologies__should_raise_ValueError():
    with pytest.raises(ValueError):
        EcoDeclaration(
            emissions={
                begin1: EmissionValues(),
                begin2: EmissionValues(),
            },
            consumed_amount={
                begin1: 100,
                begin2: 100,
            },
            technologies=EmissionValues(  # Sum of values should be 200, like consumed_amount
                CO2=200,
                NOx=100,
            ),
            resolution=EcoDeclarationResolution.hour,
            utc_offset=0,
        )


def test__EcoDeclaration__constructor__emissions_and_consumed_amount_does_not_have_the_same_keys__should_raise_ValueError():
    with pytest.raises(ValueError):
        EcoDeclaration(
            emissions={
                begin1: EmissionValues(),
                begin2: EmissionValues(),
            },
            consumed_amount={
                begin2: 100,  # Should have begin1 and begin2 as keys, like emissions
                begin3: 100,
            },
            technologies=EmissionValues(
                CO2=100,
                NOx=100,
            ),
            resolution=EcoDeclarationResolution.hour,
            utc_offset=0,
        )


def test__EcoDeclaration__constructor__not_all_emissions_have_same_keys__should_set_default_None_where_missing():
    declaration = EcoDeclaration(
        emissions={
            begin1: EmissionValues(CO2=100, NOx=100),
            begin2: EmissionValues(CO2=100, CO=100),
        },
        consumed_amount={
            begin1: 100,
            begin2: 100,
        },
        technologies=EmissionValues(
            CO2=100,
            NOx=100,
        ),
        resolution=EcoDeclarationResolution.hour,
        utc_offset=0,
    )

    assert sorted(declaration.emissions[begin1].keys()) == sorted(['CO2', 'CO', 'NOx'])
    assert sorted(declaration.emissions[begin2].keys()) == sorted(['CO2', 'CO', 'NOx'])
    assert declaration.emissions[begin1]['CO'] is None
    assert declaration.emissions[begin2]['NOx'] is None


# -- Methods -----------------------------------------------------------------


def test__EcoDeclaration__total_consumed_amount__consumed_amount_exists__should_return_correct_number():

    # Arrange
    uut = EcoDeclaration(
        emissions={
            begin1: EmissionValues(CO2=100, CH4=200),
            begin2: EmissionValues(CO2=300, CH4=400),
            begin3: EmissionValues(CO2=500, CH4=600, NOx=700),
        },
        consumed_amount={
            begin1: 10,
            begin2: 20,
            begin3: 30,
        },
        technologies=EmissionValues(
            Wind=30,
            Solar=30,
        ),
        resolution=EcoDeclarationResolution.hour,
        utc_offset=0,
    )

    # Assert
    assert uut.total_consumed_amount == 10 + 20 + 30


def test__EcoDeclaration__total_consumed_amount__NO_consumed_amount_exists__should_return_zero():

    # Arrange
    uut = EcoDeclaration(
        emissions={},
        consumed_amount={},
        technologies=EmissionValues(),
        resolution=EcoDeclarationResolution.hour,
        utc_offset=0,
    )

    # Assert
    assert uut.total_consumed_amount == 0


def test__EcoDeclaration__total_emissions__emissions_exists__should_return_EmissionValues_with_correct_values():

    # Arrange
    uut = EcoDeclaration(
        emissions={
            begin1: EmissionValues(CO2=100, CH4=200),
            begin2: EmissionValues(CO2=300, CH4=400),
            begin3: EmissionValues(CO2=500, CH4=600, NOx=700),
        },
        consumed_amount={
            begin1: 10,
            begin2: 20,
            begin3: 30,
        },
        technologies=EmissionValues(
            Wind=30,
            Solar=30,
        ),
        resolution=EcoDeclarationResolution.hour,
        utc_offset=0,
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
        consumed_amount={},
        technologies=EmissionValues(),
        resolution=EcoDeclarationResolution.hour,
        utc_offset=0,
    )

    # Assert
    assert isinstance(uut.total_emissions, EmissionValues)
    assert uut.total_emissions == {}


def test__EcoDeclaration__technologies_percentage__technologies_exists__should_return_EmissionValues_with_correct_values():

    # Arrange
    uut = EcoDeclaration(
        emissions={
            begin1: EmissionValues(CO2=100, CH4=200),
            begin2: EmissionValues(CO2=300, CH4=400),
            begin3: EmissionValues(CO2=500, CH4=600, NOx=700),
        },
        consumed_amount={
            begin1: 10,
            begin2: 20,
            begin3: 30,
        },
        technologies=EmissionValues(
            Wind=40,
            Solar=20,
        ),
        resolution=EcoDeclarationResolution.hour,
        utc_offset=0,
    )

    # Assert
    assert isinstance(uut.technologies_percentage, EmissionValues)
    assert uut.technologies_percentage == {
        'Wind': 40 / (10 + 20 + 30) * 100,
        'Solar': 20 / (10 + 20 + 30) * 100,
    }


def test__EcoDeclaration__technologies_percentage__NO_technologies_exists__should_return_empty_EmissionValues():

    # Arrange
    uut = EcoDeclaration(
        emissions={},
        consumed_amount={},
        technologies=EmissionValues(),
        resolution=EcoDeclarationResolution.hour,
        utc_offset=0,
    )

    # Assert
    assert isinstance(uut.technologies_percentage, EmissionValues)
    assert uut.technologies_percentage == {}


def test__EcoDeclaration__emissions_per_wh__consumed_amount_exists__should_return_EmissionValues_with_correct_values():

    # Arrange
    uut = EcoDeclaration(
        emissions={
            begin1: EmissionValues(CO2=100, CH4=200),
            begin2: EmissionValues(CO2=300, CH4=400),
            begin3: EmissionValues(CO2=500, CH4=600, NOx=700),
        },
        consumed_amount={
            begin1: 0,
            begin2: 20,
            begin3: 40,
        },
        technologies=EmissionValues(
            Wind=30,
            Solar=30,
        ),
        resolution=EcoDeclarationResolution.hour,
        utc_offset=0,
    )

    # Assert
    assert isinstance(uut.emissions_per_wh, dict)
    assert all(isinstance(v, EmissionValues) for v in uut.emissions_per_wh.values())
    assert uut.emissions_per_wh == {
        begin1: {'CO2': 0, 'CH4': 0, 'NOx': 0},
        begin2: {'CO2': 300/20, 'CH4': 400/20, 'NOx': 0},
        begin3: {'CO2': 500/40, 'CH4': 600/40, 'NOx': 700/40},
    }


def test__EcoDeclaration__emissions_per_wh__NO_consumed_amount_exists__should_return_empty_dict():

    # Arrange
    uut = EcoDeclaration(
        emissions={},
        consumed_amount={},
        technologies=EmissionValues(),
        resolution=EcoDeclarationResolution.hour,
        utc_offset=0,
    )

    # Assert
    assert isinstance(uut.emissions_per_wh, dict)
    assert uut.emissions_per_wh == {}


def test__EcoDeclaration__total_emissions_per_wh__emissions_exists__should_return_EmissionValues_with_correct_values():

    # Arrange
    uut = EcoDeclaration(
        emissions={
            begin1: EmissionValues(CO2=100, CH4=200),
            begin2: EmissionValues(CO2=300, CH4=400),
            begin3: EmissionValues(CO2=500, CH4=600, NOx=700),
        },
        consumed_amount={
            begin1: 0,
            begin2: 20,
            begin3: 30,
        },
        technologies=EmissionValues(
            Wind=15,
            Solar=35,
        ),
        resolution=EcoDeclarationResolution.hour,
        utc_offset=0,
    )

    # Assert
    assert isinstance(uut.total_emissions_per_wh, EmissionValues)
    assert uut.total_emissions_per_wh == {
        'CO2': (100 + 300 + 500) / (20 + 30),
        'CH4': (200 + 400 + 600) / (20 + 30),
        'NOx': 700 / (20 + 30),
    }


def test__EcoDeclaration__total_emissions_per_wh__NO_emissions_exists__should_return_empty_EmissionValues():

    # Arrange
    uut = EcoDeclaration(
        emissions={},
        consumed_amount={},
        technologies=EmissionValues(),
        resolution=EcoDeclarationResolution.hour,
        utc_offset=0,
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
        technologies=EmissionValues(),
        resolution=current_resolution,
        utc_offset=0,
    )

    # Assert
    with pytest.raises(ValueError):
        uut.as_resolution(new_resolution, 0)


def test__EcoDeclaration__as_resolution__group_by_day():

    # Arrange
    month1_day1_begin1 = datetime(2020, 1, 1, 0, 0)
    month1_day1_begin2 = datetime(2020, 1, 1, 1, 0)
    month1_day2_begin1 = datetime(2020, 1, 2, 0, 0)
    month1_day2_begin2 = datetime(2020, 1, 2, 1, 0)
    month2_day1_begin1 = datetime(2020, 2, 1, 0, 0)
    month2_day1_begin2 = datetime(2020, 2, 1, 1, 0)
    month2_day2_begin1 = datetime(2020, 2, 2, 0, 0)
    month2_day2_begin2 = datetime(2020, 2, 2, 1, 0)

    uut = EcoDeclaration(
        resolution=EcoDeclarationResolution.hour,
        utc_offset=0,
        emissions={
            month1_day1_begin1: EmissionValues(CO2=1, NO2=2),
            month1_day1_begin2: EmissionValues(CO2=3, NO2=4),
            month1_day2_begin1: EmissionValues(CO2=5, NO2=6),
            month1_day2_begin2: EmissionValues(CO2=7, NO2=8),
            month2_day1_begin1: EmissionValues(CO2=9, NO2=10),
            month2_day1_begin2: EmissionValues(CO2=11, NO2=12),
            month2_day2_begin1: EmissionValues(CO2=13, NO2=14),
            month2_day2_begin2: EmissionValues(CO2=15, NO2=16),
        },
        consumed_amount={
            month1_day1_begin1: 10,
            month1_day1_begin2: 20,
            month1_day2_begin1: 30,
            month1_day2_begin2: 40,
            month2_day1_begin1: 50,
            month2_day1_begin2: 60,
            month2_day2_begin1: 70,
            month2_day2_begin2: 80,
        },
        technologies=EmissionValues(
            Wind=180,
            Solar=180,
        ),
    )

    # Act
    new_declaration = uut.as_resolution(EcoDeclarationResolution.day, 0)

    # Assert
    assert new_declaration.emissions == {
        datetime(2020, 1, 1, 0, 0): {'CO2': 1+3, 'NO2': 2+4},      # month1_day1_begin1 + month1_day1_begin2
        datetime(2020, 1, 2, 0, 0): {'CO2': 5+7, 'NO2': 6+8},      # month1_day2_begin1 + month1_day2_begin2
        datetime(2020, 2, 1, 0, 0): {'CO2': 9+11, 'NO2': 10+12},   # month2_day1_begin2
        datetime(2020, 2, 2, 0, 0): {'CO2': 13+15, 'NO2': 14+16},  # month2_day2_begin1
    }


def test__EcoDeclaration__as_resolution__group_by_month():

    # Arrange
    month1_day1_begin1 = datetime(2020, 1, 1, 0, 0)
    month1_day1_begin2 = datetime(2020, 1, 1, 1, 0)
    month1_day2_begin1 = datetime(2020, 1, 2, 0, 0)
    month1_day2_begin2 = datetime(2020, 1, 2, 1, 0)
    month2_day1_begin1 = datetime(2020, 2, 1, 0, 0)
    month2_day1_begin2 = datetime(2020, 2, 1, 1, 0)
    month2_day2_begin1 = datetime(2020, 2, 2, 0, 0)
    month2_day2_begin2 = datetime(2020, 2, 2, 1, 0)

    uut = EcoDeclaration(
        resolution=EcoDeclarationResolution.hour,
        utc_offset=0,
        emissions={
            month1_day1_begin1: EmissionValues(CO2=1, NO2=2),
            month1_day1_begin2: EmissionValues(CO2=3, NO2=4),
            month1_day2_begin1: EmissionValues(CO2=5, NO2=6),
            month1_day2_begin2: EmissionValues(CO2=7, NO2=8),
            month2_day1_begin1: EmissionValues(CO2=9, NO2=10),
            month2_day1_begin2: EmissionValues(CO2=11, NO2=12),
            month2_day2_begin1: EmissionValues(CO2=13, NO2=14),
            month2_day2_begin2: EmissionValues(CO2=15, NO2=16),
        },
        consumed_amount={
            month1_day1_begin1: 10,
            month1_day1_begin2: 20,
            month1_day2_begin1: 30,
            month1_day2_begin2: 40,
            month2_day1_begin1: 50,
            month2_day1_begin2: 60,
            month2_day2_begin1: 70,
            month2_day2_begin2: 80,
        },
        technologies=EmissionValues(
            Wind=180,
            Solar=180,
        ),
    )

    # Act
    new_declaration = uut.as_resolution(EcoDeclarationResolution.month, 0)

    # Assert
    assert new_declaration.emissions == {
        datetime(2020, 1, 1, 0, 0): {'CO2': 1+3+5+7, 'NO2': 2+4+6+8},
        datetime(2020, 2, 1, 0, 0): {'CO2': 9+11+13+15, 'NO2': 10+12+14+16},
    }


def test__EcoDeclaration__as_resolution__group_by_year():

    # Arrange
    month1_day1_begin1 = datetime(2020, 1, 1, 0, 0)
    month1_day1_begin2 = datetime(2020, 1, 1, 1, 0)
    month1_day2_begin1 = datetime(2020, 1, 2, 0, 0)
    month1_day2_begin2 = datetime(2020, 1, 2, 1, 0)
    month2_day1_begin1 = datetime(2020, 2, 1, 0, 0)
    month2_day1_begin2 = datetime(2020, 2, 1, 1, 0)
    month2_day2_begin1 = datetime(2020, 2, 2, 0, 0)
    month2_day2_begin2 = datetime(2020, 2, 2, 1, 0)

    uut = EcoDeclaration(
        resolution=EcoDeclarationResolution.hour,
        utc_offset=0,
        emissions={
            month1_day1_begin1: EmissionValues(CO2=1, NO2=2),
            month1_day1_begin2: EmissionValues(CO2=3, NO2=4),
            month1_day2_begin1: EmissionValues(CO2=5, NO2=6),
            month1_day2_begin2: EmissionValues(CO2=7, NO2=8),
            month2_day1_begin1: EmissionValues(CO2=9, NO2=10),
            month2_day1_begin2: EmissionValues(CO2=11, NO2=12),
            month2_day2_begin1: EmissionValues(CO2=13, NO2=14),
            month2_day2_begin2: EmissionValues(CO2=15, NO2=16),
        },
        consumed_amount={
            month1_day1_begin1: 10,
            month1_day1_begin2: 20,
            month1_day2_begin1: 30,
            month1_day2_begin2: 40,
            month2_day1_begin1: 50,
            month2_day1_begin2: 60,
            month2_day2_begin1: 70,
            month2_day2_begin2: 80,
        },
        technologies=EmissionValues(
            Wind=180,
            Solar=180,
        ),
    )

    # Act
    new_declaration = uut.as_resolution(EcoDeclarationResolution.year, 0)

    # Assert
    assert new_declaration.emissions == {
        datetime(2020, 1, 1, 0, 0): {
            'CO2': 1+3+5+7+9+11+13+15,
            'NO2': 2+4+6+8+10+12+14+16,
        },
    }
