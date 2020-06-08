import marshmallow_dataclass as md

from origin import logger
from origin.http import Controller
from origin.auth import Token, require_oauth, inject_token

from .service import WebhookService
from .models import SubscribeRequest, Event


class Subscribe(Controller):
    """
    Subscribe to a webhook event.
    """
    Request = md.class_schema(SubscribeRequest)

    service = WebhookService()

    def __init__(self, event):
        """
        :param Event event:
        """
        self.event = event

    @require_oauth('openid')
    @inject_token
    def handle_request(self, request, token):
        """
        :param SubscribeRequest request:
        :param Token token:
        :rtype: bool
        """
        self.service.subscribe(
            event=self.event,
            subject=token.subject,
            url=request.url,
            secret=request.secret,
        )

        logger.info(f'Webhook subscription created: {self.event.value}', extra={
            'subject': token.subject,
            'event': self.event.value,
            'url': request.url,
        })

        return True
