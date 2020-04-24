# from enum import Enum
#
# from .models import Batch, BatchState
#
#
# class LedgerState(Enum):
#     """
#     States in which a Batch can exist
#     """
#     PENDING = 'PENDING'
#     COMMITTED = 'COMMITTED'
#     INVALID = 'INVALID'
#     UNKNOWN = 'UNKNOWN'
#
#
# class BatchProcessor(object):
#
#     def submit_batch(self, batch):
#         """
#         :param Batch batch:
#         """
#         pass
#
#     def check_batch_status(self, batch):
#         """
#         :param Batch batch:
#         :rtype: LedgerState
#         """
#         return LedgerState.COMMITTED
