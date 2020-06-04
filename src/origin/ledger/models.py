import sqlalchemy as sa
import origin_ledger_sdk as ols
from sqlalchemy import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declared_attr
from enum import Enum

from origin.db import ModelBase, Session

from .keys import KeyGenerator


class BatchState(Enum):
    """
    States in which a Batch can exist
    """
    # Step 1: The batch has been submitted to the database
    PENDING = 'PENDING'
    # Step 2: The batch has been submitted to the ledger
    SUBMITTED = 'SUBMITTED'
    # Step 3/1: The batch failed to be processed on the ledger
    DECLINED = 'DECLINED'
    # Step 3/2: The batch was processes successfully on the ledger
    COMPLETED = 'COMPLETED'


class Batch(ModelBase):
    """
    TODO
    """
    __tablename__ = 'ledger_batch'

    id = sa.Column(sa.Integer(), primary_key=True, index=True)
    created = sa.Column(sa.DateTime(timezone=True), server_default=sa.func.now())
    state: BatchState = sa.Column(sa.Enum(BatchState), nullable=False)

    # Time when batch was LAST submitted to ledger (if at all)
    submitted = sa.Column(sa.DateTime(timezone=True), nullable=True)

    # Relationships
    user_id = sa.Column(sa.Integer(), sa.ForeignKey('auth_user.id'), index=True, nullable=False)
    user = relationship('User', foreign_keys=[user_id])
    transactions = relationship('Transaction', back_populates='batch', uselist=True)

    # The handle returned by the ledger used to enquiry for status
    handle = sa.Column(sa.String())

    # How many times the ledger has been polled, asking for batch status
    poll_count = sa.Column(sa.Integer(), nullable=False, default=0)

    def add_transaction(self, transaction):
        """
        :param Transaction transaction:
        """
        transaction.order = len(self.transactions)
        self.transactions.append(transaction)

    def add_all_transactions(self, transactions):
        """
        :param collections.abc.Iterable[Transaction] transactions:
        """
        for transaction in transactions:
            self.add_transaction(transaction)

    def on_begin(self):
        """
        TODO
        """
        self.state = BatchState.PENDING

        for transaction in self.transactions:
            transaction.on_begin()

    def on_submitted(self, handle):
        """
        TODO

        :param str handle:
        """
        self.state = BatchState.SUBMITTED
        self.handle = handle
        self.submitted = func.now()

    def on_commit(self):
        """
        TODO
        """
        self.state = BatchState.COMPLETED

        for transaction in self.transactions:
            transaction.on_commit()

    def on_rollback(self):
        """
        TODO
        """
        self.state = BatchState.DECLINED

        session = Session.object_session(self)

        for transaction in reversed(self.transactions):
            transaction.on_rollback()
            session.delete(transaction)

    def build_ledger_batch(self):
        """
        TODO
        """
        batch = ols.Batch(self.user.key.PrivateKey())

        for transaction in self.transactions:
            batch.add_request(transaction.build_ledger_request())

        return batch


class Transaction(ModelBase):
    """
    TODO
    """
    __abstract__ = False
    __tablename__ = 'ledger_transaction'
    __table_args__ = (
        sa.UniqueConstraint('parent_ggo_id'),
        sa.UniqueConstraint('batch_id', 'order'),
    )

    id = sa.Column(sa.Integer(), primary_key=True, index=True)
    order = sa.Column(sa.Integer(), nullable=False)

    # Polymorphism
    type = sa.Column(sa.String(20), nullable=False)
    __mapper_args__ = {
        'polymorphic_on': type,
        'polymorphic_identity': 'transaction',
    }

    @declared_attr
    def batch_id(cls):
        return sa.Column(sa.Integer(), sa.ForeignKey('ledger_batch.id'), index=True, nullable=False)

    @declared_attr
    def batch(cls):
        return relationship('Batch', foreign_keys=[cls.batch_id], back_populates='transactions')

    @declared_attr
    def parent_ggo_id(cls):
        return sa.Column(sa.Integer(), sa.ForeignKey('ggo_ggo.id'), index=True, nullable=False)

    @declared_attr
    def parent_ggo(cls):
        return relationship('Ggo', foreign_keys=[cls.parent_ggo_id])

    def on_begin(self):
        """
        TODO
        """
        raise NotImplementedError

    def on_commit(self):
        """
        TODO
        """
        raise NotImplementedError

    def on_rollback(self):
        """
        TODO
        """
        raise NotImplementedError

    def build_ledger_request(self):
        """
        TODO
        """
        raise NotImplementedError


class SplitTransaction(Transaction):
    """
    TODO
    """
    __abstract__ = False
    __tablename__ = 'ledger_transaction'
    __mapper_args__ = {'polymorphic_identity': 'split'}
    __table_args__ = (
        {'extend_existing': True},
    )

    # The target GGOs (children)
    targets = relationship('SplitTarget', back_populates='transaction', uselist=True)

    def add_target(self, ggo, reference=None):
        """
        :param Ggo ggo:
        :param str reference:
        """
        self.targets.append(SplitTarget(
            transaction=self,
            reference=reference,
            ggo=ggo,
        ))

    def on_begin(self):
        """
        TODO
        """
        assert sum(t.ggo.amount for t in self.targets) == self.parent_ggo.amount
        assert self.parent_ggo.stored is True
        assert self.parent_ggo.retired is False
        assert self.parent_ggo.locked is False
        assert self.parent_ggo.synchronized is True

        self.parent_ggo.stored = False
        self.parent_ggo.locked = True
        self.parent_ggo.synchronized = False

        for target in self.targets:
            target.ggo.stored = False
            target.ggo.locked = True
            target.ggo.synchronized = False

    def on_commit(self):
        """
        TODO
        """
        self.parent_ggo.stored = False
        self.parent_ggo.locked = False
        self.parent_ggo.synchronized = True

        for target in self.targets:
            target.ggo.stored = True
            target.ggo.locked = False
            target.ggo.synchronized = True

    def on_rollback(self):
        """
        TODO WHAT EVEN TODO HERE?
        """
        self.parent_ggo.stored = True
        self.parent_ggo.locked = False
        self.parent_ggo.synchronized = True

        session = Session.object_session(self)

        for target in self.targets:
            session.delete(target)
            session.delete(target.ggo)

    def build_ledger_request(self):
        parts = []

        for target in self.targets:
            parts.append(ols.SplitGGOPart(
                address=target.ggo.address,
                amount=target.ggo.amount,
            ))

        return ols.SplitGGORequest(
            source_private_key=self.parent_ggo.key.PrivateKey(),
            source_address=self.parent_ggo.address,
            parts=parts,
        )


class SplitTarget(ModelBase):
    """
    TODO
    """
    __tablename__ = 'ledger_split_target'
    __table_args__ = (
        sa.UniqueConstraint('ggo_id'),
    )

    id = sa.Column(sa.Integer(), primary_key=True, index=True)

    transaction_id = sa.Column(sa.Integer(), sa.ForeignKey('ledger_transaction.id'), index=True)
    transaction = relationship('SplitTransaction', foreign_keys=[transaction_id])

    ggo_id = sa.Column(sa.Integer(), sa.ForeignKey('ggo_ggo.id'), index=True)
    ggo = relationship('Ggo', foreign_keys=[ggo_id])

    # Client reference, like Agreement ID etc.
    reference = sa.Column(sa.String(), index=True)


class RetireTransaction(Transaction):
    """
    TODO
    """
    __abstract__ = False
    __tablename__ = 'ledger_transaction'
    __mapper_args__ = {'polymorphic_identity': 'retire'}
    __table_args__ = (
        {'extend_existing': True},
    )

    # The begin of the measurement
    begin = sa.Column(sa.DateTime(timezone=True))

    # The meteringpoint which the measurement were published to
    meteringpoint_id = sa.Column(sa.Integer(), sa.ForeignKey('accounts_meteringpoint.id'))
    meteringpoint = relationship('MeteringPoint', foreign_keys=[meteringpoint_id])

    # Ledger address of the measurement to retire GGO to
    measurement_address = sa.Column(sa.String())

    @staticmethod
    def build(ggo, meteringpoint, measurement_address):
        """
        Retires the provided GGO to the measurement at the provided address.
        The provided meteringpoint

        :param Ggo ggo:
        :param MeteringPoint meteringpoint:
        :param str measurement_address:
        :rtype: RetireTransaction
        """
        ggo.retire_gsrn = meteringpoint.gsrn
        ggo.retire_address = measurement_address

        return RetireTransaction(
            parent_ggo=ggo,
            begin=ggo.begin,
            meteringpoint=meteringpoint,
            measurement_address=measurement_address,
        )

    def on_begin(self):
        """
        TODO
        """
        self.parent_ggo.stored = False
        self.parent_ggo.retired = True
        self.parent_ggo.locked = True
        self.parent_ggo.synchronized = False

    def on_commit(self):
        """
        TODO
        """
        self.parent_ggo.stored = False
        self.parent_ggo.retired = True
        self.parent_ggo.locked = False
        self.parent_ggo.synchronized = True

    def on_rollback(self):
        """
        TODO WHAT EVEN TODO HERE?
        """
        self.parent_ggo.stored = True  # TODO test this
        self.parent_ggo.retired = False
        self.parent_ggo.locked = False
        self.parent_ggo.synchronized = True
        self.parent_ggo.retire_gsrn = None  # TODO test this
        self.parent_ggo.retire_address = None  # TODO test this

    def build_ledger_request(self):
        """
        TODO
        """
        measurement_key = KeyGenerator.get_key_for_measurement(
            self.meteringpoint, self.begin)

        settlement_address = ols.generate_address(
            ols.AddressPrefix.SETTLEMENT, measurement_key.PublicKey())

        return ols.RetireGGORequest(
            settlement_address=settlement_address,
            measurement_address=self.measurement_address,
            measurement_private_key=measurement_key.PrivateKey(),
            parts=[
                ols.RetireGGOPart(
                    address=ols.generate_address(ols.AddressPrefix.GGO, self.parent_ggo.key.PublicKey()),
                    private_key=self.parent_ggo.key.PrivateKey(),
                )
            ],
        )
