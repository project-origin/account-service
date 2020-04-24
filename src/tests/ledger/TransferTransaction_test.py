# import pytest
# from unittest.mock import Mock
#
# from origin.ledger import TransferTransaction
# from origin.ggo import Ggo
#
#
# # TODO: Test model constraints
#
#
# def test__TransferTransaction__TODO(session, user1, user2):
#     """
#     :param Session session:
#     :param User user1:
#     :param User user2:
#     """
#     # Arrange
#     facility1 = Mock()
#     facility2 = Mock()
#     distribution.add(facility1, 25)
#     distribution.add(facility2, 75)
#
#     # Act + Assert
#     assert distribution.size() == 2
#     assert distribution.total() == 100
#     assert distribution.get(facility1) == 25
#     assert distribution.get(facility2) == 75
#
#     assert len(distribution.facilities()) == 2
#     assert facility1 in distribution.facilities()
#     assert facility2 in distribution.facilities()
#
#     assert len(list(distribution)) == 2
#     assert (facility1, 25) in list(distribution)
#     assert (facility2, 75) in list(distribution)
#
#     with pytest.raises(AssertionError):
#         distribution.one()
