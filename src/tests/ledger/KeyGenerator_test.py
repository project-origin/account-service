from datetime import datetime, timezone
from unittest.mock import Mock
from bip32utils import BIP32Key

from origin.ledger.keys import KeyGenerator


A_VALID_EXTENDED_KEY = (
    'xprv9s21ZrQH143K2CK5syo8PdeX5Y4TYFkcU'
    'KonHhm1e7znhaKj6odQFbbBa7T2Y77AtiNmU6'
    'aatP2qJBTwvhqxvaSBHA9hEfZ5gViAS3bBj7F'
)

A_VALID_KEY = BIP32Key.fromExtendedKey(A_VALID_EXTENDED_KEY)


def test__KeyGenerator__get_key_for_user():

    # Arrange
    user = Mock(master_extended_key=A_VALID_EXTENDED_KEY)

    # Act
    key = KeyGenerator.get_key_for_user(user)

    # Assert
    assert key.ExtendedKey() == A_VALID_EXTENDED_KEY


def test__KeyGenerator__set_key_for_user():

    # Arrange
    user = Mock()

    # Act
    KeyGenerator.set_key_for_user(user, A_VALID_KEY)

    # Assert
    assert user.master_extended_key == A_VALID_EXTENDED_KEY


def test__KeyGenerator__set_key_for_user_from_entropy():

    # Arrange
    entropy = b'SomethingVeryRandomWithAMinimumLengthWhichIDontQuiteRememberRightNow'
    user = Mock()

    # Act
    KeyGenerator.set_key_for_user_from_entropy(user, entropy)

    # Assert
    assert user.master_extended_key == BIP32Key.fromEntropy(entropy).ExtendedKey()


def test__KeyGenerator__get_key_for_metering_point():

    # Arrange
    user = Mock(master_extended_key=A_VALID_EXTENDED_KEY)
    meteringpoint = Mock(user=user, key_index=123)

    # Act
    key = KeyGenerator.get_key_for_metering_point(meteringpoint)

    # Assert
    assert key.ExtendedKey() == A_VALID_KEY.ChildKey(1).ChildKey(123).ExtendedKey()


def test__KeyGenerator__get_key_for_measurement():

    # Arrange
    input_begin = datetime(2020, 1, 1, 0, 0, 12, 21, tzinfo=timezone.utc)
    user = Mock(master_extended_key=A_VALID_EXTENDED_KEY)
    meteringpoint = Mock(user=user, key_index=123)

    # Act
    key = KeyGenerator.get_key_for_measurement(meteringpoint, input_begin)

    # Assert
    assert key.ExtendedKey() == A_VALID_KEY.ChildKey(1).ChildKey(123).ChildKey(1577836800).ExtendedKey()


def test__KeyGenerator__get_key_for_traded_ggo_at_index():

    # Arrange
    user = Mock(master_extended_key=A_VALID_EXTENDED_KEY)

    # Act
    key = KeyGenerator.get_key_for_traded_ggo_at_index(user, 123)

    # Assert
    assert key.ExtendedKey() == A_VALID_KEY.ChildKey(0).ChildKey(123).ExtendedKey()


def test__KeyGenerator__get_key_for_traded_ggo():

    # Arrange
    user = Mock(master_extended_key=A_VALID_EXTENDED_KEY)
    ggo = Mock(user=user, key_index=123, issued=False)

    # Act
    key = KeyGenerator.get_key_for_traded_ggo(ggo)

    # Assert
    assert key.ExtendedKey() == A_VALID_KEY.ChildKey(0).ChildKey(123).ExtendedKey()


def test__KeyGenerator__get_key_for_issued_ggo():

    # Arrange
    user = Mock(master_extended_key=A_VALID_EXTENDED_KEY)
    ggo = Mock(
        begin=datetime(2020, 1, 1, 0, 0, 12, 21, tzinfo=timezone.utc),
        issued=True,
        issue_meteringpoint=Mock(user=user, key_index=123),
    )

    # Act
    key = KeyGenerator.get_key_for_issued_ggo(ggo)

    # Assert
    assert key.ExtendedKey() == A_VALID_KEY.ChildKey(1).ChildKey(123).ChildKey(1577836800).ExtendedKey()
