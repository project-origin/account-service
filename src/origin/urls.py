from .ggo import controllers as ggo
from .auth import controllers as auth
from .webhooks import controllers as webhooks

from .webhooks import Event


urls = (

    # Auth / Users
    ('/auth/login', auth.Login()),
    ('/auth/login/callback', auth.LoginCallback()),

    ('/ggo', ggo.GetGgoList()),
    ('/ggo/summary', ggo.GetGgoSummary()),
    ('/compose', ggo.ComposeGgo()),
    ('/transfer', ggo.TransferGgo()),
    ('/transfer/summary', ggo.GetTransferSummary()),
    ('/transfer/get-transferred-amount', ggo.GetTransferredAmount()),

    # Retiring
    ('/retire/get-retired-amount', ggo.GetRetiredAmount()),

    # Transferring
    # ('/compose', trading.ComposeGgo()),
    # ('/transfer/transactions', trading.GetTransferList()),
    # ('/transfer/summary', trading.GetTransferSummary()),
    # ('/transfer/get-transferred-amount', trading.GetTransferredAmount()),

    # Webhooks
    ('/webhook/on-ggos-issued', ggo.OnGgosIssuedWebhook()),
    ('/webhook/on-meteringpoints-available', auth.OnMeteringPointsAvailableWebhook()),
    ('/webhook/on-ggo-received/subscribe', webhooks.Subscribe(
        Event.ON_GGO_RECEIVED)),

)
