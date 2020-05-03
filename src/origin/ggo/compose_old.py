from functools import lru_cache

from origin.auth import User, UserQuery, MeteringPointQuery
from origin.services.datahub import (
    DataHubService,
    Measurement,
    GetMeasurementRequest,
)
from origin.ledger import (
    Batch,
    BatchState,
    SplitTransaction,
    RetireTransaction,
)

from .queries import RetireQuery
from .models import Ggo, TransferRequest, RetireRequest


datahub = DataHubService()


class GgoComposer(object):
    """
    TODO
    """

    class AmountUnavailable(Exception):
        pass

    class RetireGSRNInvalid(Exception):
        def __init__(self, ggo, gsrn):
            self.ggo = ggo
            self.gsrn = gsrn

    class RetireMeasurementInvalid(Exception):
        def __init__(self, ggo, measurement):
            self.ggo = ggo
            self.measurement = measurement

    def __init__(self, ggo, token, session):
        """
        :param Ggo ggo:
        :param str token:
        :param Session session:
        """
        assert ggo.is_tradable()

        self.ggo = ggo
        self.user = ggo.user
        self.token = token
        self.session = session
        self.transfers = []
        self.retires = []

    def __len__(self):
        """
        :rtype: int
        """
        return len(self.transfers) + len(self.retires)

    @property
    def total_amount(self):
        """
        :rtype: int
        """
        sum_of_transfers = sum(req.amount for req in self.transfers)
        sum_of_retires = sum(req.amount for req, meteringpoint, measurement in self.retires)
        return sum_of_transfers + sum_of_retires

    @property
    def remaining_amount(self):
        """
        :rtype: int
        """
        return max(0, self.ggo.amount - self.total_amount)

    def add_transfer(self, request):
        """
        :param TransferRequest request:
        """
        assert request.amount > 0

        self.transfers.append(request)

    def add_many_transfers(self, requests):
        """
        :param list[TransferRequest] requests:
        """
        for request in requests:
            self.add_transfer(request)

    def add_retire(self, request):
        """
        :param RetireRequest request:
        """
        assert request.amount > 0

        # The meteringpoint which we want to retire to,
        # and which the measurement were published to
        meteringpoint = self.get_metering_point(request.gsrn)  # TODO filter only consumption?

        # TODO what if metering_point is None?
        if meteringpoint is None:
            raise self.RetireGSRNInvalid(self.ggo, meteringpoint.gsrn)

        # The published consumption measurement (fetched from DataHub service)
        measurement = self.get_consumption(meteringpoint.gsrn, self.ggo.begin)

        # GGO may be in different sector etc.
        if not self.ggo.can_retire_measurement(measurement):
            raise self.RetireMeasurementInvalid(self.ggo, measurement)

        # Amount already retired on this measurement
        retired_amount = self.get_retired_amount(measurement)

        # Amount remaining for entire Measurement to be retired completely
        remaining_amount = measurement.amount - retired_amount

        # The actual amount to retire cannot exceed the remaining amount
        actual_amount = min(remaining_amount, request.amount)

        if actual_amount > 0:
            request.amount = actual_amount
            self.retires.append((request, meteringpoint, measurement))

    def add_many_retires(self, requests):
        """
        :param list[RetireRequest] requests:
        """
        for request in requests:
            self.add_retire(request)

    def compose(self):
        """
        :rtype: GgoComposition
        """
        if self.total_amount > self.ggo.amount:
            raise self.AmountUnavailable

        # List of (Ggo, User, reference)
        transfers = []

        # List of (RetireRequest, Ggo, Measurement)
        retires = []

        # Create a split target + RetireTransaction for each retire
        for request, meteringpoint, measurement in self.retires:
            new_ggo = self.ggo.create_child(request.amount, self.user)
            retires.append((
                request,
                new_ggo,
                meteringpoint,
                measurement,
            ))

        # Create a split target for each transfer
        for request in self.transfers:
            target_user = self.get_user(request.sub)
            new_ggo = self.ggo.create_child(request.amount, target_user)
            transfers.append((
                new_ggo,
                target_user,
                request.reference,
            ))

        # Transfer the remaining amount to the current owner of the GGO
        if self.remaining_amount > 0:
            new_ggo = self.ggo.create_child(self.remaining_amount, self.user)
            transfers.append((
                new_ggo,
                self.user,
                None,
            ))

        return GgoComposition(self.ggo, self.user, transfers, retires)

    def get_user(self, sub):
        """
        :param str sub:
        :rtype: User
        """
        return UserQuery(self.session) \
            .has_sub(sub) \
            .one()

    def get_metering_point(self, gsrn):
        """
        :param str gsrn:
        :rtype: MeteringPoint
        """
        return MeteringPointQuery(self.session) \
            .belongs_to(self.ggo.user) \
            .has_gsrn(gsrn) \
            .one_or_none()

    def get_consumption(self, gsrn, begin):
        """
        :param str gsrn:
        :param datetime.datetime begin:
        :rtype: Measurement
        """
        request = GetMeasurementRequest(gsrn=gsrn, begin=begin)
        response = datahub.get_consumption(
            self.ggo.user.access_token, request)

        return response.measurement

    def get_retired_amount(self, measurement):
        """
        :param Measurement measurement:
        :rtype: int
        """
        return RetireQuery(self.session) \
            .belongs_to(self.ggo.user) \
            .is_retired_to_address(measurement.address) \
            .get_total_amount()


class GgoComposition(object):
    def __init__(self, ggo, user, transfers, retires):
        """
        :param Ggo ggo:
        :param User user:
        :param list[(Ggo, User, str)] transfers:
        :param list[(RetireRequest, Ggo, MeteringPoint, Measurement)] retires:
        """
        self.ggo = ggo
        self.user = user
        self.transfers = transfers
        self.retires = retires

    @property
    @lru_cache()
    def recipients(self):
        """
        :rtype: list[(User, Ggo)]
        """
        return [(ggo, user) for ggo, user, reference in self.transfers]

    @property
    @lru_cache()
    def batch(self):
        """
        :rtype: Batch
        """
        retire_transactions = []
        split_transaction = SplitTransaction(parent_ggo=self.ggo)

        # Create a split target + RetireTransaction for each retire
        for request, ggo, meteringpoint, measurement in self.retires:
            ggo.retire_gsrn = request.gsrn
            ggo.retire_address = measurement.address

            split_transaction.add_target(ggo)
            retire_transactions.append(RetireTransaction.build(
                ggo=ggo,
                meteringpoint=meteringpoint,
                measurement_address=measurement.address,
            ))

        # Create a split target for each transfer
        for ggo, user, reference in self.transfers:
            split_transaction.add_target(ggo, reference)

        # First add the SplitTransaction, then the RetireTransactions,
        # as they require the SplitTransaction to complete first
        batch = Batch(user=self.user, state=BatchState.PENDING)
        batch.add_transaction(split_transaction)
        batch.add_all_transactions(retire_transactions)
        batch.on_begin()

        return batch
