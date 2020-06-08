from origin.auth import User, MeteringPoint
from origin.ledger import Batch, SplitTransaction, RetireTransaction
from origin.services.datahub import (
    DataHubService,
    Measurement,
    GetMeasurementRequest,
)

from .queries import RetireQuery
from .models import Ggo


datahub = DataHubService()


class GgoComposer(object):
    """
    Implements functionality to transfer and/or retire a GGO.

    The method build_batch() compiles together a Batch object, which can
    be save to the database, and later executed on the ledger. It creates
    a Batch with Transactions, along with the necessary new Ggo(s).
    """

    class Empty(Exception):
        """
        Raised when composing a Batch if no transfers or retires were provided
        """
        pass

    class AmountUnavailable(Exception):
        """
        Raised if the sum of transfers+retires exceeds the GGO provided
        """
        pass

    class RetireMeasurementUnavailable(Exception):
        """
        Raised when trying to retire to a measurement that doesn't exists
        """
        def __init__(self, gsrn, begin):
            self.gsrn = gsrn
            self.begin = begin

    class RetireMeasurementInvalid(Exception):
        """
        Raised when trying to retire to a measurement that it can not
        retire to
        """
        def __init__(self, ggo, measurement):
            self.ggo = ggo
            self.measurement = measurement

    def __init__(self, ggo, session):
        """
        :param Ggo ggo: The GGO to transfer/retire
        :param sqlalchemy.orm.Session session:
        """
        assert ggo.is_tradable()
        assert not ggo.is_expired()

        self.ggo = ggo
        self.session = session
        self.transfers = []
        self.retires = []

    @property
    def total_amount(self):
        """
        Returns the total amount of all added transfers and retires.

        :rtype: int
        """
        sum_of_transfers = sum(t[1] for t in self.transfers)
        sum_of_retires = sum(r[2] for r in self.retires)
        return sum_of_transfers + sum_of_retires

    @property
    def remaining_amount(self):
        """
        Returns the remaining available amount to transfer and/or retire.

        :rtype: int
        """
        return self.ggo.amount - self.total_amount

    def add_transfer(self, user, amount, reference=None):
        """
        Transfer the provided amount to the provided user.
        Optionally adds an arbitrary reference string for future enquiry.

        :param User user:
        :param int amount:
        :param str reference:
        """
        assert 0 < amount <= self.ggo.amount

        self.transfers.append((user, amount, reference))

    def add_retire(self, meteringpoint, amount):
        """
        Transfer the provided amount to the provided meteringpoint.

        :param MeteringPoint meteringpoint:
        :param int amount:
        """
        assert 0 < amount <= self.ggo.amount
        assert meteringpoint.user_id == self.ggo.user_id

        # The published consumption measurement to retire to
        measurement = self.get_consumption(meteringpoint.gsrn, self.ggo.begin)

        if measurement is None:
            raise self.RetireMeasurementUnavailable(
                meteringpoint.gsrn, self.ggo.begin)

        # GGO may be in different sector etc.
        if not self.eligible_to_retire_measurement(measurement):
            raise self.RetireMeasurementInvalid(
                self.ggo, measurement)

        # The actual amount to retire may not exceed the measured
        # amount minus whats already been retired
        retired_amount = self.get_retired_amount(measurement)
        remaining_amount = measurement.amount - retired_amount
        actual_amount = min(remaining_amount, amount)

        if actual_amount > 0:
            self.retires.append((measurement, meteringpoint, actual_amount))

    # -- Compose  ------------------------------------------------------------

    def build_batch(self):
        """
        Returns the Batch along with a list of tuples of (User, Ggo)
        where User is the recipient of the [new] Ggo. One

        :rtype: (Batch, list[(User, Ggo)])
        """
        if self.total_amount == 0:
            raise self.Empty
        if self.total_amount > self.ggo.amount:
            raise self.AmountUnavailable

        split_transaction = SplitTransaction(parent_ggo=self.ggo)
        retire_transactions = []
        recipients = []

        # Assign the remaining amount to the current owner of the GGO
        if self.remaining_amount > 0:
            self.add_transfer(self.ggo.user, self.remaining_amount)

        # For debugging/development/assurance
        assert self.total_amount == self.ggo.amount
        assert self.remaining_amount == 0

        # Do not create a SplitTransaction if there's only one retire,
        # and this constitutes the entire amount of the GGO. In this
        # case we can retire the GGO directly. Otherwise we have to
        # split it up before transferring/retiring.
        total_targets = len(self.transfers) + len(self.retires)
        should_split = total_targets > 1 or len(self.transfers) > 0

        # -- Transfers -------------------------------------------------------

        for user, amount, reference in self.transfers:
            assert should_split
            ggo_to_transfer = self.ggo.create_child(amount, user)
            split_transaction.add_target(ggo_to_transfer, reference)
            recipients.append((user, ggo_to_transfer))

        # -- Retires ---------------------------------------------------------

        for measurement, meteringpoint, amount in self.retires:
            if should_split:
                ggo_to_retire = self.ggo.create_child(amount, self.ggo.user)
                split_transaction.add_target(ggo_to_retire)
                retire_transactions.append(RetireTransaction.build(
                    ggo=ggo_to_retire,
                    meteringpoint=meteringpoint,
                    measurement_address=measurement.address,
                ))
            else:
                retire_transactions.append(RetireTransaction.build(
                    ggo=self.ggo,
                    meteringpoint=meteringpoint,
                    measurement_address=measurement.address,
                ))

        # -- Setup Batch -----------------------------------------------------

        batch = Batch(user=self.ggo.user)

        if should_split:
            batch.add_transaction(split_transaction)
        if retire_transactions:
            batch.add_all_transactions(retire_transactions)

        # Batch and transactions initial state
        batch.on_begin()

        return batch, recipients

    # -- Helper functions  ---------------------------------------------------

    def eligible_to_retire_measurement(self, measurement):
        """
        Check whether the GGO is eligible to be retired to the
        provided measurement.

        :param Measurement measurement:
        :rtype: bool
        """
        return (self.ggo.sector == measurement.sector
                and self.ggo.begin == measurement.begin)

    def get_retired_amount(self, measurement):
        """
        Get the already retired amount for a specific measurement.

        :param Measurement measurement:
        :rtype: int
        """
        return RetireQuery(self.session) \
            .belongs_to(self.ggo.user) \
            .is_retired_to_address(measurement.address) \
            .get_total_amount()

    def get_consumption(self, gsrn, begin):
        """
        Returns a single Measurement for a GSRN at a specific begin.

        The GSRN provided MUST belong to the user who owns the
        GGO to transfer/retire, fails otherwise.

        :param str gsrn:
        :param datetime.datetime begin:
        :rtype: Measurement
        """
        request = GetMeasurementRequest(gsrn=gsrn, begin=begin)
        response = datahub.get_consumption(
            self.ggo.user.access_token, request)

        return response.measurement
