from .ggo import controllers as ggo
from .auth import controllers as auth
from .webhooks import controllers as webhooks
from .webhooks import WebhookEvent


urls = (

    # Auth / Users
    ('/auth/login', auth.Login()),
    ('/auth/login/callback', auth.LoginCallback()),

    # Accounts
    ('/accounts', auth.GetAccounts()),

    ('/ggo', ggo.GetGgoList()),
    ('/ggo/compose', ggo.ComposeGgo()),
    ('/ggo/summary', ggo.GetGgoSummary()),
    ('/ggo/get-total-amount', ggo.GetTotalAmount()),

    # Transfers
    ('/transfer/summary', ggo.GetTransferSummary()),
    ('/transfer/get-total-amount', ggo.GetTransferredAmount()),

    # Webhooks
    ('/webhook/on-ggos-issued', ggo.OnGgosIssuedWebhook()),
    ('/webhook/on-meteringpoints-available', auth.OnMeteringPointsAvailableWebhook()),
    ('/webhook/on-ggo-received/subscribe', webhooks.Subscribe(WebhookEvent.ON_GGO_RECEIVED)),
    ('/webhook/on-ggo-received/unsubscribe', webhooks.Unsubscribe(WebhookEvent.ON_GGO_RECEIVED)),

    # TODO
    # Remove these once ExampleBackend is been changed to make use
    # of /ggo/compose in stead (be for backwards compatibility)
    ('/compose', ggo.ComposeGgo()),
    ('/transfer/get-transferred-amount', ggo.GetTransferredAmount()),

)
