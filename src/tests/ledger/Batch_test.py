import origin_ledger_sdk as ols
from unittest.mock import MagicMock, Mock, patch

from origin.ledger.models import Batch, BatchState


def test__Batch__add_transaction__should_set_correct_order_on_transaction():

    # Arrange
    transaction1 = MagicMock()
    transaction2 = MagicMock()
    transaction3 = MagicMock()
    transaction4 = MagicMock()
    transaction5 = MagicMock()

    uut = Batch()

    # Act
    uut.add_transaction(transaction1)
    uut.add_transaction(transaction2)
    uut.add_transaction(transaction3)
    uut.add_all_transactions([transaction4, transaction5])

    # Assert
    assert transaction1.order == 0
    assert transaction2.order == 1
    assert transaction3.order == 2
    assert transaction4.order == 3
    assert transaction5.order == 4


def test__Batch__on_begin__should_set_batch_state_to_PENDING_and_invoke_on_begin_on_transactions():

    # Arrange
    transactions = [MagicMock(), MagicMock(), MagicMock()]

    uut = Batch()
    uut.add_all_transactions(transactions)

    # Act
    uut.on_begin()

    # Assert
    assert uut.state is BatchState.PENDING

    for transaction in transactions:
        transaction.on_begin.assert_called_once()


def test__Batch__on_submitted__should_set_batch_state_to_SUBMITTED_and_save_handle_to_self():

    # Arrange
    handle = MagicMock()
    uut = Batch()

    # Act
    uut.on_submitted(handle)

    # Assert
    assert uut.state is BatchState.SUBMITTED
    assert uut.handle is handle


def test__Batch__on_commit__should_set_batch_state_to_COMPLETED_and_invoke_on_commit_on_transactions():

    # Arrange
    transactions = [MagicMock(), MagicMock(), MagicMock()]
    uut = Batch()
    uut.add_all_transactions(transactions)

    # Act
    uut.on_commit()

    # Assert
    assert uut.state is BatchState.COMPLETED

    for transaction in transactions:
        transaction.on_commit.assert_called_once()


@patch('origin.ledger.models.Session.object_session')
def test__Batch__on_rollback__should_set_batch_state_to_DECLINED_and_invoke_on_rollback_on_transactions(object_session):

    session_mock = MagicMock()
    object_session.return_value = session_mock

    # Arrange
    transactions = [MagicMock(), MagicMock(), MagicMock()]
    uut = Batch()
    uut.add_all_transactions(transactions)

    # Act
    uut.on_rollback()

    # Assert
    assert uut.state is BatchState.DECLINED
    assert session_mock.delete.call_count == 3
    session_mock.delete.assert_any_call(transactions[0])
    session_mock.delete.assert_any_call(transactions[1])
    session_mock.delete.assert_any_call(transactions[2])

    for transaction in transactions:
        transaction.on_rollback.assert_called_once()


def test__Batch__build_ledger_batch__should_build_correct_request():

    # Arrange
    user = Mock()
    transactions = [MagicMock(), MagicMock(), MagicMock()]

    uut = Batch(user=user)
    uut.add_all_transactions(transactions)

    # Act
    request = uut.build_ledger_batch()

    # Assert
    assert type(request) is ols.Batch

    for transaction in transactions:
        transaction.build_ledger_request.assert_called_once_with()
