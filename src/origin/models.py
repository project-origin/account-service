from .ggo import Ggo, GgoIndexSequence, Technology
from .auth import User, MeteringPoint, MeteringPointIndexSequence
from .webhooks import WebhookSubscription
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
    GgoIndexSequence,
    Technology,
    User,
    MeteringPoint,
    MeteringPointIndexSequence,
    Batch,
    Transaction,
    SplitTransaction,
    RetireTransaction,
    WebhookSubscription,
)
