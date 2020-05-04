from unittest.mock import MagicMock

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

    # Act
    uut.add_all_transactions(transactions)
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

    # Act
    uut.add_all_transactions(transactions)
    uut.on_commit()

    # Assert
    assert uut.state is BatchState.COMPLETED

    for transaction in transactions:
        transaction.on_commit.assert_called_once()


def test__Batch__on_commit__should_set_batch_state_to_DECLINED_and_invoke_on_rollback_on_transactions():

    # Arrange
    transactions = [MagicMock(), MagicMock(), MagicMock()]
    uut = Batch()

    # Act
    uut.add_all_transactions(transactions)
    uut.on_rollback()

    # Assert
    assert uut.state is BatchState.DECLINED

    for transaction in transactions:
        transaction.on_rollback.assert_called_once()
