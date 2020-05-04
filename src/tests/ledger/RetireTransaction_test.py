import pytest
import origin_ledger_sdk as ols
from unittest.mock import MagicMock, patch, Mock

from origin.ledger.models import RetireTransaction


def test__RetireTransaction__build__should_instantiate_object_correctly():

    # Arrange
    parent_ggo = MagicMock()
    meteringpoint = MagicMock()
    measurement_address = 'foobar'

    # Act
    transaction = RetireTransaction.build(
        parent_ggo, meteringpoint, measurement_address)

    # Assert
    assert transaction.parent_ggo is parent_ggo
    assert transaction.begin is parent_ggo.begin
    assert transaction.meteringpoint is meteringpoint
    assert transaction.measurement_address == measurement_address


def test__RetireTransaction__on_begin__should_update_state_on_self_and_target_ggos():

    # Arrange
    parent_ggo = MagicMock(
        amount=100,
        stored=True,
        retired=False,
        locked=False,
        synchronized=True,
    )

    uut = RetireTransaction(parent_ggo=parent_ggo)

    # Act
    uut.on_begin()

    # Assert
    assert parent_ggo.stored is False
    assert parent_ggo.retired is True
    assert parent_ggo.locked is True
    assert parent_ggo.synchronized is False


def test__RetireTransaction__on_commit__should_update_state_on_self_and_target_ggos():

    # Arrange
    parent_ggo = MagicMock(
        amount=100,
        stored=False,
        retired=True,
        locked=True,
        synchronized=False,
    )

    uut = RetireTransaction(parent_ggo=parent_ggo)

    # Act
    uut.on_commit()

    # Assert
    assert parent_ggo.stored is False
    assert parent_ggo.retired is True
    assert parent_ggo.locked is False
    assert parent_ggo.synchronized is True


def test__RetireTransaction__on_rollback__should_update_state_on_self_and_target_ggos():

    # Arrange
    parent_ggo = MagicMock(
        amount=100,
        stored=False,
        retired=True,
        locked=True,
        synchronized=False,
    )

    uut = RetireTransaction(parent_ggo=parent_ggo)

    # Act
    uut.on_rollback()

    # Assert
    assert parent_ggo.stored is False
    assert parent_ggo.retired is False
    assert parent_ggo.locked is False
    assert parent_ggo.synchronized is True


@patch('origin.ledger.models.KeyGenerator.get_key_for_measurement')
@patch('origin.ledger.models.ols.generate_address')
def test__RetireTransaction__build_ledger_request__should_build_correct_request(
        generate_address, get_key_for_measurement):

    def __generate_address_mock(address_prefix, key):
        if address_prefix is ols.AddressPrefix.SETTLEMENT:
            return 'settlement_address'
        elif address_prefix is ols.AddressPrefix.GGO:
            return 'ggo_address'
        else:
            raise ValueError

    # Arrange
    parent_ggo = MagicMock()
    meteringpoint = MagicMock()
    measurement_address = 'foobar'
    measurement_key = Mock()

    get_key_for_measurement.return_value = measurement_key
    generate_address.side_effect = __generate_address_mock

    uut = RetireTransaction.build(
        parent_ggo, meteringpoint, measurement_address)

    # Act
    request = uut.build_ledger_request()

    # Assert
    generate_address.assert_any_call(ols.AddressPrefix.SETTLEMENT, measurement_key.PublicKey())
    generate_address.assert_any_call(ols.AddressPrefix.GGO, parent_ggo.key.PublicKey())

    assert type(request) is ols.RetireGGORequest
    assert request.settlement_address == 'settlement_address'
    assert request.measurement_address == measurement_address
    assert request.measurement_private_key is measurement_key.PrivateKey()
    assert len(request.parts) == 1
    assert type(request.parts[0]) is ols.RetireGGOPart
    assert request.parts[0].address == 'ggo_address'
    assert request.parts[0].private_key == parent_ggo.key.PrivateKey()
