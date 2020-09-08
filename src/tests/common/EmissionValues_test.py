import pytest

from origin.common import EmissionValues


ev1 = EmissionValues(
    carbon_dioxide=1,
    methane=2,
    nitrous_oxide=3,
    greenhouse_gasses=4,
    sulfur_dioxide=5,
    nitrogen_dioxide=6,
    carbon_monoxide=7,
    hydrocarbons=8,
    particles=9,
    coal_fly_ash=10,
    coal_slag=11,
    desulfuriazion_products=12,
    slag=13,
    rga=14,
    bioash=15,
    radioactive_waste=16,
)

ev2 = EmissionValues(
    carbon_dioxide=100,
    methane=200,
    nitrous_oxide=300,
    greenhouse_gasses=400,
    sulfur_dioxide=500,
    nitrogen_dioxide=600,
    carbon_monoxide=700,
    hydrocarbons=800,
    particles=900,
    coal_fly_ash=1000,
    coal_slag=1100,
    desulfuriazion_products=1200,
    slag=1300,
    rga=1400,
    bioash=1500,
    radioactive_waste=1600,
)


@pytest.mark.parametrize('i', (-1, 0, 1, 100, -1.0, 0.0, 1.0, 100.0))
def test__EmissionValues__add_integer_or_float(i):

    # Act
    ev3 = ev1 + i
    ev4 = i + ev1

    # Assert
    assert ev4['carbon_dioxide'] == ev4['carbon_dioxide'] == ev1['carbon_dioxide'] + i
    assert ev4['methane'] == ev3['methane'] == ev1['methane'] + i
    assert ev4['nitrous_oxide'] == ev3['nitrous_oxide'] == ev1['nitrous_oxide'] + i
    assert ev4['greenhouse_gasses'] == ev3['greenhouse_gasses'] == ev1['greenhouse_gasses'] + i
    assert ev4['sulfur_dioxide'] == ev3['sulfur_dioxide'] == ev1['sulfur_dioxide'] + i
    assert ev4['nitrogen_dioxide'] == ev3['nitrogen_dioxide'] == ev1['nitrogen_dioxide'] + i
    assert ev4['carbon_monoxide'] == ev3['carbon_monoxide'] == ev1['carbon_monoxide'] + i
    assert ev4['hydrocarbons'] == ev3['hydrocarbons'] == ev1['hydrocarbons'] + i
    assert ev4['particles'] == ev3['particles'] == ev1['particles'] + i
    assert ev4['coal_fly_ash'] == ev3['coal_fly_ash'] == ev1['coal_fly_ash'] + i
    assert ev4['coal_slag'] == ev3['coal_slag'] == ev1['coal_slag'] + i
    assert ev4['desulfuriazion_products'] == ev3['desulfuriazion_products'] == ev1['desulfuriazion_products'] + i
    assert ev4['slag'] == ev3['slag'] == ev1['slag'] + i
    assert ev4['rga'] == ev3['rga'] == ev1['rga'] + i
    assert ev4['bioash'] == ev3['bioash'] == ev1['bioash'] + i
    assert ev4['radioactive_waste'] == ev3['radioactive_waste'] == ev1['radioactive_waste'] + i


def test__EmissionValues__add_two_together():

    # Act
    ev3 = ev1 + ev2
    ev4 = ev2 + ev1

    # Assert
    assert ev4['carbon_dioxide'] == ev3['carbon_dioxide'] == 101
    assert ev4['methane'] == ev3['methane'] == 202
    assert ev4['nitrous_oxide'] == ev3['nitrous_oxide'] == 303
    assert ev4['greenhouse_gasses'] == ev3['greenhouse_gasses'] == 404
    assert ev4['sulfur_dioxide'] == ev3['sulfur_dioxide'] == 505
    assert ev4['nitrogen_dioxide'] == ev3['nitrogen_dioxide'] == 606
    assert ev4['carbon_monoxide'] == ev3['carbon_monoxide'] == 707
    assert ev4['hydrocarbons'] == ev3['hydrocarbons'] == 808
    assert ev4['particles'] == ev3['particles'] == 909
    assert ev4['coal_fly_ash'] == ev3['coal_fly_ash'] == 1010
    assert ev4['coal_slag'] == ev3['coal_slag'] == 1111
    assert ev4['desulfuriazion_products'] == ev3['desulfuriazion_products'] == 1212
    assert ev4['slag'] == ev3['slag'] == 1313
    assert ev4['rga'] == ev3['rga'] == 1414
    assert ev4['bioash'] == ev3['bioash'] == 1515
    assert ev4['radioactive_waste'] == ev3['radioactive_waste'] == 1616


@pytest.mark.parametrize('i', (-1, 0, 1, 100, -1.0, 0.0, 1.0, 100.0))
def test__EmissionValues__multiply_integer_or_float(i):

    # Act
    ev3 = ev1 * i
    ev4 = i * ev1

    # Assert
    assert ev4['carbon_dioxide'] == ev4['carbon_dioxide'] == ev1['carbon_dioxide'] * i
    assert ev4['methane'] == ev3['methane'] == ev1['methane'] * i
    assert ev4['nitrous_oxide'] == ev3['nitrous_oxide'] == ev1['nitrous_oxide'] * i
    assert ev4['greenhouse_gasses'] == ev3['greenhouse_gasses'] == ev1['greenhouse_gasses'] * i
    assert ev4['sulfur_dioxide'] == ev3['sulfur_dioxide'] == ev1['sulfur_dioxide'] * i
    assert ev4['nitrogen_dioxide'] == ev3['nitrogen_dioxide'] == ev1['nitrogen_dioxide'] * i
    assert ev4['carbon_monoxide'] == ev3['carbon_monoxide'] == ev1['carbon_monoxide'] * i
    assert ev4['hydrocarbons'] == ev3['hydrocarbons'] == ev1['hydrocarbons'] * i
    assert ev4['particles'] == ev3['particles'] == ev1['particles'] * i
    assert ev4['coal_fly_ash'] == ev3['coal_fly_ash'] == ev1['coal_fly_ash'] * i
    assert ev4['coal_slag'] == ev3['coal_slag'] == ev1['coal_slag'] * i
    assert ev4['desulfuriazion_products'] == ev3['desulfuriazion_products'] == ev1['desulfuriazion_products'] * i
    assert ev4['slag'] == ev3['slag'] == ev1['slag'] * i
    assert ev4['rga'] == ev3['rga'] == ev1['rga'] * i
    assert ev4['bioash'] == ev3['bioash'] == ev1['bioash'] * i
    assert ev4['radioactive_waste'] == ev3['radioactive_waste'] == ev1['radioactive_waste'] * i


def test__EmissionValues__multiply_two_together():

    # Act
    ev3 = ev1 * ev2
    ev4 = ev2 * ev1

    # Assert
    assert ev4['carbon_dioxide'] == ev3['carbon_dioxide'] == 1 * 100
    assert ev4['methane'] == ev3['methane'] == 2 * 200
    assert ev4['nitrous_oxide'] == ev3['nitrous_oxide'] == 3 * 300
    assert ev4['greenhouse_gasses'] == ev3['greenhouse_gasses'] == 4 * 400
    assert ev4['sulfur_dioxide'] == ev3['sulfur_dioxide'] == 5 * 500
    assert ev4['nitrogen_dioxide'] == ev3['nitrogen_dioxide'] == 6 * 600
    assert ev4['carbon_monoxide'] == ev3['carbon_monoxide'] == 7 * 700
    assert ev4['hydrocarbons'] == ev3['hydrocarbons'] == 8 * 800
    assert ev4['particles'] == ev3['particles'] == 9 * 900
    assert ev4['coal_fly_ash'] == ev3['coal_fly_ash'] == 10 * 1000
    assert ev4['coal_slag'] == ev3['coal_slag'] == 11 * 1100
    assert ev4['desulfuriazion_products'] == ev3['desulfuriazion_products'] == 12* 1200
    assert ev4['slag'] == ev3['slag'] == 13 * 1300
    assert ev4['rga'] == ev3['rga'] == 14 * 1400
    assert ev4['bioash'] == ev3['bioash'] == 15 * 1500
    assert ev4['radioactive_waste'] == ev3['radioactive_waste'] == 16 * 1600
