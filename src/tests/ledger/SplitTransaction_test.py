import pytest
import origin_ledger_sdk as ols
from unittest.mock import MagicMock, patch

from origin.ledger.models import SplitTransaction, SplitTarget


def test__SplitTransaction__add_target__should_save_target_to_self():

    # Arrange
    ggo1 = MagicMock(amount=50)
    ggo2 = MagicMock(amount=50)
    uut = SplitTransaction(parent_ggo=MagicMock(amount=100))

    # Act
    uut.add_target(ggo1, 'REF1')
    uut.add_target(ggo2, 'REF2')

    # Assert
    assert len(uut.targets) == 2
    assert uut.targets[0].ggo is ggo1
    assert uut.targets[0].reference is 'REF1'
    assert uut.targets[1].ggo is ggo2
    assert uut.targets[1].reference is 'REF2'


@pytest.mark.parametrize('child1_amount, child2_amount', (
    (10, 10),
    (100, 100),
    (0, 101),
    (101, 0),
    (0, 0),
))
def test__SplitTransaction__on_begin__sum_of_new_ggos_amount_does_not_match_parent_ggo_amount__should_raise_AssertionError(
        child1_amount, child2_amount):

    # Arrange
    uut = SplitTransaction(parent_ggo=MagicMock(
        amount=100,
        stored=True,
        retired=False,
        locked=False,
        synchronized=True,
    ))

    uut.add_target(MagicMock(amount=child1_amount))
    uut.add_target(MagicMock(amount=child2_amount))

    # Act + Assert
    with pytest.raises(AssertionError):
        uut.on_begin()


@pytest.mark.parametrize(
    'stored, retired, locked, synchronized', (
    (False,  False,   False,  True),
    (True,   True,    False,  True),
    (True,   False,   True,   True),
    (True,   False,   False,  False),
))
def test__SplitTransaction__on_begin__invalid_parent_ggo__should_raise_AssertionError(
        stored, retired, locked, synchronized):

    """
    A valid parent_ggo has:
        stored = True
        retired = False
        locked = False
        synchronized = True
    """

    # Arrange
    uut = SplitTransaction(parent_ggo=MagicMock(
        amount=100,
        stored=stored,
        retired=retired,
        locked=locked,
        synchronized=synchronized,
    ))

    uut.add_target(MagicMock(amount=50))
    uut.add_target(MagicMock(amount=50))

    # Act + Assert
    with pytest.raises(AssertionError):
        uut.on_begin()


def test__SplitTransaction__on_begin__valid_parent_ggo__should_update_state_on_self_and_target_ggos():

    # Arrange
    parent_ggo = MagicMock(
        amount=100,
        stored=True,
        retired=False,
        locked=False,
        synchronized=True,
    )

    target_ggo1 = MagicMock(amount=50)
    target_ggo2 = MagicMock(amount=50)

    uut = SplitTransaction(parent_ggo=parent_ggo)
    uut.add_target(target_ggo1)
    uut.add_target(target_ggo2)

    # Act
    uut.on_begin()

    # Assert
    assert parent_ggo.stored is False
    assert parent_ggo.locked is True
    assert parent_ggo.synchronized is False

    assert target_ggo1.stored is False
    assert target_ggo1.locked is True
    assert target_ggo1.synchronized is False

    assert target_ggo2.stored is False
    assert target_ggo2.locked is True
    assert target_ggo2.synchronized is False


def test__SplitTransaction__on_commit__should_update_state_on_self_and_target_ggos():

    # Arrange
    parent_ggo = MagicMock(
        amount=100,
        stored=False,
        retired=False,
        locked=True,
        synchronized=False,
    )

    target_ggo1 = MagicMock(
        amount=50,
        stored=False,
        retired=False,
        locked=True,
        synchronized=False,
    )
    target_ggo2 = MagicMock(
        amount=50,
        stored=False,
        retired=False,
        locked=True,
        synchronized=False,
    )

    uut = SplitTransaction(parent_ggo=parent_ggo)
    uut.targets.append(SplitTarget(ggo=target_ggo1))
    uut.targets.append(SplitTarget(ggo=target_ggo2))

    # Act
    uut.on_commit()

    # Assert
    assert parent_ggo.stored is False
    assert parent_ggo.locked is False
    assert parent_ggo.synchronized is True

    assert target_ggo1.stored is True
    assert target_ggo1.locked is False
    assert target_ggo1.synchronized is True

    assert target_ggo2.stored is True
    assert target_ggo2.locked is False
    assert target_ggo2.synchronized is True


@patch('origin.ledger.models.Session.object_session')
def test__SplitTransaction__on_rollback__should_update_state_on_self_and_target_ggos(object_session):

    session_mock = MagicMock()
    object_session.return_value = session_mock

    # Arrange
    parent_ggo = MagicMock(
        amount=100,
        stored=False,
        retired=False,
        locked=True,
        synchronized=False,
    )

    target_ggo1 = MagicMock(
        amount=50,
        stored=False,
        retired=False,
        locked=True,
        synchronized=False,
    )
    target_ggo2 = MagicMock(
        amount=50,
        stored=False,
        retired=False,
        locked=True,
        synchronized=False,
    )

    uut = SplitTransaction(parent_ggo=parent_ggo)
    uut.targets.append(SplitTarget(ggo=target_ggo1))
    uut.targets.append(SplitTarget(ggo=target_ggo2))

    # Act
    uut.on_rollback()

    # Assert
    assert parent_ggo.stored is True
    assert parent_ggo.locked is False
    assert parent_ggo.synchronized is True

    assert session_mock.delete.call_count == 4
    session_mock.delete.assert_any_call(uut.targets[0])
    session_mock.delete.assert_any_call(uut.targets[1])
    session_mock.delete.assert_any_call(target_ggo1)
    session_mock.delete.assert_any_call(target_ggo1)


def test__SplitTransaction__build_ledger_request__should_build_correct_request():

    # Arrange
    parent_ggo = MagicMock()
    target_ggo1 = MagicMock()
    target_ggo2 = MagicMock()

    uut = SplitTransaction(parent_ggo=parent_ggo)
    uut.targets.append(SplitTarget(ggo=target_ggo1))
    uut.targets.append(SplitTarget(ggo=target_ggo2))

    # Act
    request = uut.build_ledger_request()

    # Assert
    assert type(request) is ols.SplitGGORequest
    assert request.source_private_key is parent_ggo.key.PrivateKey()
    assert request.source_address == parent_ggo.address
    assert len(request.parts) == 2

    assert request.parts[0].address == target_ggo1.address
    assert request.parts[0].amount == target_ggo1.amount

    assert request.parts[1].address == target_ggo2.address
    assert request.parts[1].amount == target_ggo2.amount
