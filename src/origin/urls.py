from .ggo import controllers as ggo
from .auth import controllers as auth
from .forecast import controllers as forecast
from .webhooks import controllers as webhooks
from .webhooks import WebhookEvent


urls = (

    # Auth / Users
    ('/auth/login', auth.Login()),
    ('/auth/login/callback', auth.LoginCallback()),

    # Accounts
    ('/accounts', auth.GetAccounts()),
    ('/accounts/find-suppliers', auth.FindSuppliers()),

    ('/ggo', ggo.GetGgoList()),
    ('/ggo/compose', ggo.ComposeGgo()),
    ('/ggo/summary', ggo.GetGgoSummary()),
    ('/ggo/get-total-amount', ggo.GetTotalAmount()),

    # Transfers
    ('/transfer/summary', ggo.GetTransferSummary()),
    ('/transfer/get-total-amount', ggo.GetTransferredAmount()),

    # Forecasts
    ('/forecast', forecast.GetForecast()),
    ('/forecast/list', forecast.GetForecastList()),
    ('/forecast/series', forecast.GetForecastSeries()),
    ('/forecast/submit', forecast.SubmitForecast()),

    # Webhooks
    ('/webhook/on-ggo-issued', ggo.OnGgoIssuedWebhook()),
    ('/webhook/on-meteringpoint-available', auth.OnMeteringPointAvailableWebhook()),
    ('/webhook/on-ggo-received/subscribe', webhooks.Subscribe(WebhookEvent.ON_GGO_RECEIVED)),
    ('/webhook/on-ggo-received/unsubscribe', webhooks.Unsubscribe(WebhookEvent.ON_GGO_RECEIVED)),
    ('/webhook/on-forecast-received/subscribe', webhooks.Subscribe(WebhookEvent.ON_FORECAST_RECEIVED)),
    ('/webhook/on-forecast-received/unsubscribe', webhooks.Unsubscribe(WebhookEvent.ON_FORECAST_RECEIVED)),

    # TODO
    # Remove these once ExampleBackend is been changed to make use
    # of /ggo/compose in stead (be for backwards compatibility)
    ('/compose', ggo.ComposeGgo()),
    ('/transfer/get-transferred-amount', ggo.GetTransferredAmount()),

    # TODO
    # Remove once AccountService doesn't use these anymore
    ('/webhook/on-ggos-issued', ggo.OnGgoIssuedWebhook()),
    ('/webhook/on-meteringpoints-available', auth.OnMeteringPointsAvailableWebhook()),

)
