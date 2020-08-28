from datetime import datetime, timezone

from origin.common import EmissionValues
from origin.services.energytypes import EmissionData, EmissionPart


def test__EmissionData__amount__has_parts___should_return_sum_of_parts():
    uut = EmissionData(
        sector='DK1',
        timestamp_utc=datetime(2020, 1, 1, 1, 0, tzinfo=timezone.utc),
        parts=[
            EmissionPart(technology='A', amount=111, emissions=EmissionValues()),
            EmissionPart(technology='B', amount=222, emissions=EmissionValues()),
            EmissionPart(technology='C', amount=333, emissions=EmissionValues()),
        ],
    )

    assert uut.amount == 111 + 222 + 333


def test__EmissionData__amount__has_NO_parts___should_return_zero():
    uut = EmissionData(
        sector='DK1',
        timestamp_utc=datetime(2020, 1, 1, 1, 0, tzinfo=timezone.utc),
        parts=[],
    )

    assert uut.amount == 0


def test__EmissionData__emissions__has_parts___should_return_sum_of_parts_as_EmissionValues():
    uut = EmissionData(
        sector='DK1',
        timestamp_utc=datetime(2020, 1, 1, 1, 0, tzinfo=timezone.utc),
        parts=[
            EmissionPart(technology='A', amount=111, emissions=EmissionValues(CO2=100, CO=200)),
            EmissionPart(technology='B', amount=222, emissions=EmissionValues(CO2=300, CO=400, NOx=500)),
            EmissionPart(technology='C', amount=333, emissions=EmissionValues(CO=600, NOx=700)),
        ],
    )

    assert isinstance(uut.emissions, EmissionValues)
    assert uut.emissions == {
        'CO2': 100 + 300,
        'CO': 200 + 400 + 600,
        'NOx': 500 + 700,
    }


def test__EmissionData__emissions__has_NO_parts___should_return_empty_EmissionValues():
    uut = EmissionData(
        sector='DK1',
        timestamp_utc=datetime(2020, 1, 1, 1, 0, tzinfo=timezone.utc),
        parts=[],
    )

    assert isinstance(uut.emissions, EmissionValues)
    assert uut.emissions == {}


def test__EmissionData__emissions_per_wh__has_parts___should_return_emissions_per_wh_as_EmissionValues():
    uut = EmissionData(
        sector='DK1',
        timestamp_utc=datetime(2020, 1, 1, 1, 0, tzinfo=timezone.utc),
        parts=[
            EmissionPart(technology='A', amount=111, emissions=EmissionValues(CO2=100, CO=200)),
            EmissionPart(technology='B', amount=222, emissions=EmissionValues(CO2=300, CO=400, NOx=500)),
            EmissionPart(technology='C', amount=333, emissions=EmissionValues(CO=600, NOx=700)),
        ],
    )

    assert isinstance(uut.emissions_per_wh, EmissionValues)
    assert uut.emissions_per_wh == {
        'CO2': (100 + 300) / (111 + 222 + 333),
        'CO': (200 + 400 + 600) / (111 + 222 + 333),
        'NOx': (500 + 700) / (111 + 222 + 333),
    }


def test__EmissionData__emissions_per_wh__has_parts_but_amount_is_zero___should_return_empty_EmissionValues():
    uut = EmissionData(
        sector='DK1',
        timestamp_utc=datetime(2020, 1, 1, 1, 0, tzinfo=timezone.utc),
        parts=[
            EmissionPart(technology='A', amount=0, emissions=EmissionValues(CO2=100, CO=200)),
            EmissionPart(technology='B', amount=0, emissions=EmissionValues(CO2=300, CO=400, NOx=500)),
            EmissionPart(technology='C', amount=0, emissions=EmissionValues(CO=600, NOx=700)),
        ],
    )

    assert isinstance(uut.emissions_per_wh, EmissionValues)
    assert uut.emissions_per_wh == {}


def test__EmissionData__emissions_per_wh__has_NO_parts___should_return_empty_EmissionValues():
    uut = EmissionData(
        sector='DK1',
        timestamp_utc=datetime(2020, 1, 1, 1, 0, tzinfo=timezone.utc),
        parts=[],
    )

    assert isinstance(uut.emissions_per_wh, EmissionValues)
    assert uut.emissions_per_wh == {}


def test__EmissionData__technologies__has_parts___should_return_technologies_as_EmissionValues():
    uut = EmissionData(
        sector='DK1',
        timestamp_utc=datetime(2020, 1, 1, 1, 0, tzinfo=timezone.utc),
        parts=[
            EmissionPart(technology='Solar', amount=111, emissions=EmissionValues(CO2=100, CO=200)),
            EmissionPart(technology='Wind', amount=222, emissions=EmissionValues(CO2=300, CO=400, NOx=500)),
            EmissionPart(technology='Coal', amount=333, emissions=EmissionValues(CO=600, NOx=700)),
        ],
    )

    assert isinstance(uut.technologies, EmissionValues)
    assert uut.technologies == {
        'Solar': 111,
        'Wind': 222,
        'Coal': 333,
    }


def test__EmissionData__technologies__has_NO_parts___should_return_empty_EmissionValues():
    uut = EmissionData(
        sector='DK1',
        timestamp_utc=datetime(2020, 1, 1, 1, 0, tzinfo=timezone.utc),
        parts=[],
    )

    assert isinstance(uut.technologies, EmissionValues)
    assert uut.technologies == {}


def test__EmissionData__technologies_share__has_parts___should_return_technologies_share_as_EmissionValues():
    uut = EmissionData(
        sector='DK1',
        timestamp_utc=datetime(2020, 1, 1, 1, 0, tzinfo=timezone.utc),
        parts=[
            EmissionPart(technology='Solar', amount=111, emissions=EmissionValues(CO2=100, CO=200)),
            EmissionPart(technology='Wind', amount=222, emissions=EmissionValues(CO2=300, CO=400, NOx=500)),
            EmissionPart(technology='Coal', amount=333, emissions=EmissionValues(CO=600, NOx=700)),
        ],
    )

    assert isinstance(uut.technologies_share, EmissionValues)
    assert uut.technologies_share == {
        'Solar': 111 / (111 + 222 + 333),
        'Wind': 222 / (111 + 222 + 333),
        'Coal': 333 / (111 + 222 + 333),
    }


def test__EmissionData__technologies_share__has_NO_parts___should_return_empty_EmissionValues():
    uut = EmissionData(
        sector='DK1',
        timestamp_utc=datetime(2020, 1, 1, 1, 0, tzinfo=timezone.utc),
        parts=[],
    )

    assert isinstance(uut.technologies_share, EmissionValues)
    assert uut.technologies_share == {}
