# from unittest.mock import MagicMock, patch
# from datetime import datetime
#
# from origin.ggo import Ggo
# from origin.ledger import TransferTransaction, SplitTransaction, BatchState
# from origin.trading import BatchBuilder, TransferClaim
#
#
# def _setup_GgoQuery_mock(mock, ggos):
#     mock.return_value = mock
#     mock.apply_filters.return_value = mock
#     mock.belongs_to.return_value = mock
#     mock.is_tradable.return_value = mock
#     mock.order_by.return_value = mock
#     mock.get_distinct_begins.return_value = sorted(set(ggo.begin for ggo in ggos))
#     mock.begins_at.side_effect = lambda begin: _setup_GgoQuery_mock(
#         MagicMock(), [ggo for ggo in ggos if ggo.begin == begin])
#     mock.__iter__.return_value = iter(ggos)
#     return mock
#
#
# @patch('origin.trading.batches.GgoQuery')
# def test__BatchBuilder__build_batches(mock_ggo_query, user1, user2):
#     """
#     :param User user1:
#     :param User user2:
#     :param Mock mock_ggo_query:
#     """
#
#     # -- Arrange -------------------------------------------------------------
#
#     ggo1 = Ggo(
#         user=user1,
#         amount=100,
#         gsrn='1',
#         sector='DK1',
#         begin=datetime(2020, 1, 1, 0, 0),
#         end=datetime(2020, 1, 1, 1, 0),
#         technology_code='T010000',
#         fuel_code='F01050100',
#     )
#
#     ggo2 = Ggo(
#         user=user1,
#         amount=100,
#         gsrn='1',
#         sector='DK1',
#         begin=datetime(2020, 1, 1, 0, 0),
#         end=datetime(2020, 1, 1, 1, 0),
#         technology_code='T010000',
#         fuel_code='F01050100',
#     )
#
#     ggo3 = Ggo(
#         user=user1,
#         amount=100,
#         gsrn='1',
#         sector='DK1',
#         begin=datetime(2020, 1, 1, 1, 0),
#         end=datetime(2020, 1, 1, 2, 0),
#         technology_code='T010000',
#         fuel_code='F01050100',
#     )
#
#     ggo4 = Ggo(
#         user=user1,
#         amount=50,
#         gsrn='1',
#         sector='DK1',
#         begin=datetime(2020, 1, 1, 2, 0),
#         end=datetime(2020, 1, 1, 3, 0),
#         technology_code='T010000',
#         fuel_code='F01050100',
#     )
#
#     _setup_GgoQuery_mock(mock_ggo_query, [ggo1, ggo2, ggo3, ggo4])
#
#     claim = TransferClaim(
#         user_from=user1,
#         user_to=user2,
#         amount=150,
#         precise=False,
#         reference='MYREF',
#     )
#
#     # -- Act -----------------------------------------------------------------
#
#     batches = list(BatchBuilder().build_batches(claim, None))
#
#     # -- Assert --------------------------------------------------------------
#
#     mock_ggo_query.apply_filters.assert_called_with(claim.filters)
#     mock_ggo_query.belongs_to.assert_called_with(claim.user_from)
#     mock_ggo_query.is_tradable.assert_called()
#
#     # Should produce one Batch for each distinct Ggo.begin
#     assert len(batches) == 3
#
#     # -- Assert on Batch with Ggo.begin: 2020-01-01 00:00 --------------------
#
#     assert batches[0].user_id == user1.id
#     assert batches[0].status == BatchState.PENDING
#     assert len(batches[0].transactions) == 2
#
#     # The first transaction should transfer the entire GGO (amount=100)
#     assert isinstance(batches[0].transactions[0], TransferTransaction)
#     assert batches[0].transactions[0].parent_ggo == ggo1
#     assert batches[0].transactions[0].target_ggo.amount == ggo1.amount
#     assert batches[0].transactions[0].target_ggo.user == user2
#
#     # The second transaction should split into two parts (each amount=50)
#     assert isinstance(batches[0].transactions[1], SplitTransaction)
#     assert batches[0].transactions[1].parent_ggo == ggo2
#     assert batches[0].transactions[1].keep_ggo.user == user1
#     assert batches[0].transactions[1].keep_ggo.amount == 50
#     assert batches[0].transactions[1].trade_ggo.user == user2
#     assert batches[0].transactions[1].trade_ggo.amount == 50
#
#     # -- Assert on Batch with Ggo.begin: 2020-01-01 01:00 --------------------
#
#     assert batches[1].user_id == user1.id
#     assert batches[1].status == BatchState.PENDING
#     assert len(batches[1].transactions) == 1
#     assert batches[1].transactions[0].parent_ggo == ggo3
#     assert batches[1].transactions[0].target_ggo.user == user2
#     assert batches[1].transactions[0].target_ggo.amount == 100
#
#     # -- Assert on Batch with Ggo.begin: 2020-01-01 02:00 --------------------
#
#     assert batches[2].user_id == user1.id
#     assert batches[2].status == BatchState.PENDING
#     assert len(batches[2].transactions) == 1
#     assert batches[2].transactions[0].parent_ggo == ggo4
#     assert batches[2].transactions[0].target_ggo.user == user2
#     assert batches[2].transactions[0].target_ggo.amount == 50
