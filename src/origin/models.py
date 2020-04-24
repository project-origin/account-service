from .ggo import Ggo
from .auth import User, MeteringPoint
from .webhooks import Subscription
from .ledger import (
    Batch,
    Transaction,
    SplitTransaction,
    RetireTransaction,
)


# This is a list of all database models to include
# when creating database migrations.

VERSIONED_DB_MODELS = (
    Ggo,
    User,
    MeteringPoint,
    Batch,
    Transaction,
    SplitTransaction,
    RetireTransaction,
    Subscription,
)
