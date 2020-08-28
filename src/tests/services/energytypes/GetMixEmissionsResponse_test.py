import marshmallow_dataclass as md
from datetime import datetime, timezone

from origin.common import EmissionValues
from origin.services.energytypes import GetMixEmissionsResponse


def test__GetMixEmissionsResponse__should_map_data_correctly():
    source_json = {
        "success": True,
        "mix_emissions": [
            {
                "timestamp_utc": "2019-09-17T22:00:00.000Z",
                "sector": "DK1",
                "technology": "Wind",
                "amount": 1000,
                "CO2": 111,
                "CH4": 222,
            },
            {
                "timestamp_utc": "2019-09-17T22:00:00.000Z",
                "sector": "DK1",
                "technology": "Solar",
                "amount": 2000,
                "CO2": 333,
                "CH4": 444,
            },
            {
                "timestamp_utc": "2019-09-17T23:00:00.000Z",
                "sector": "DK1",
                "technology": "Wind",
                "amount": 3000,
                "CO2": 555,
                "CH4": 666,
            },
            {
                "timestamp_utc": "2019-09-17T23:00:00.000Z",
                "sector": "DK1",
                "technology": "Solar",
                "amount": 4000,
                "CO2": 777,
                "CH4": 888,
            },
            {
                "timestamp_utc": "2019-09-17T22:00:00.000Z",
                "sector": "DK2",
                "technology": "Wind",
                "amount": 5000,
                "CO2": 999,
                "CH4": 101010,
            },
            {
                "timestamp_utc": "2019-09-17T22:00:00.000Z",
                "sector": "DK2",
                "technology": "Solar",
                "amount": 6000,
                "CO2": 111111,
                "CH4": 121212,
            },
            {
                "timestamp_utc": "2019-09-17T23:00:00.000Z",
                "sector": "DK2",
                "technology": "Wind",
                "amount": 7000,
                "CO2": 131313,
                "CH4": 141414,
            },
            {
                "timestamp_utc": "2019-09-17T23:00:00.000Z",
                "sector": "DK2",
                "technology": "Solar",
                "amount": 8000,
                "CO2": 151515,
                "CH4": 161616,
            },
        ]
    }

    schema = md.class_schema(GetMixEmissionsResponse)
    schema_instance = schema()
    model = schema_instance.load(source_json)

    assert len(model.mix_emissions) == 4
    assert len(model.mix_emissions[0].parts) == 2
    assert len(model.mix_emissions[1].parts) == 2
    assert len(model.mix_emissions[2].parts) == 2
    assert len(model.mix_emissions[3].parts) == 2

    assert model.mix_emissions[0].timestamp_utc == datetime(2019, 9, 17, 22, 0, 0, 0, tzinfo=timezone.utc)
    assert model.mix_emissions[0].sector == 'DK1'
    assert model.mix_emissions[0].parts[0].technology == 'Wind'
    assert model.mix_emissions[0].parts[0].amount == 1000
    assert model.mix_emissions[0].parts[0].emissions == {'CO2': 111, 'CH4': 222}
    assert model.mix_emissions[0].parts[1].technology == 'Solar'
    assert model.mix_emissions[0].parts[1].amount == 2000
    assert model.mix_emissions[0].parts[1].emissions == {'CO2': 333, 'CH4': 444}

    assert model.mix_emissions[1].timestamp_utc == datetime(2019, 9, 17, 23, 0, 0, 0, tzinfo=timezone.utc)
    assert model.mix_emissions[1].sector == 'DK1'
    assert model.mix_emissions[1].parts[0].technology == 'Wind'
    assert model.mix_emissions[1].parts[0].amount == 3000
    assert model.mix_emissions[1].parts[0].emissions == {'CO2': 555, 'CH4': 666}
    assert model.mix_emissions[1].parts[1].technology == 'Solar'
    assert model.mix_emissions[1].parts[1].amount == 4000
    assert model.mix_emissions[1].parts[1].emissions == {'CO2': 777, 'CH4': 888}

    assert model.mix_emissions[2].timestamp_utc == datetime(2019, 9, 17, 22, 0, 0, 0, tzinfo=timezone.utc)
    assert model.mix_emissions[2].sector == 'DK2'
    assert model.mix_emissions[2].parts[0].technology == 'Wind'
    assert model.mix_emissions[2].parts[0].amount == 5000
    assert model.mix_emissions[2].parts[0].emissions == {'CO2': 999, 'CH4': 101010}
    assert model.mix_emissions[2].parts[1].technology == 'Solar'
    assert model.mix_emissions[2].parts[1].amount == 6000
    assert model.mix_emissions[2].parts[1].emissions == {'CO2': 111111, 'CH4': 121212}

    assert model.mix_emissions[3].timestamp_utc == datetime(2019, 9, 17, 23, 0, 0, 0, tzinfo=timezone.utc)
    assert model.mix_emissions[3].sector == 'DK2'
    assert model.mix_emissions[3].parts[0].technology == 'Wind'
    assert model.mix_emissions[3].parts[0].amount == 7000
    assert model.mix_emissions[3].parts[0].emissions == {'CO2': 131313, 'CH4': 141414}
    assert model.mix_emissions[3].parts[1].technology == 'Solar'
    assert model.mix_emissions[3].parts[1].amount == 8000
    assert model.mix_emissions[3].parts[1].emissions == {'CO2': 151515, 'CH4': 161616}
