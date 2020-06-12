import json
import hmac
import requests
import marshmallow_dataclass as md
from hashlib import sha256
from base64 import b64encode

from origin import logger
from origin.settings import DEBUG, HMAC_HEADER
from origin.db import atomic
from origin.ggo import Ggo

from .models import (
    WebhookEvent,
    WebhookSubscription,
    OnGgoReceivedRequest,
)


class WebhookConnectionError(Exception):
    """
    Raised when publishing an event to a webhook results
    in a connection error.
    """
    pass


class WebhookError(Exception):
    """
    Raised when publishing an event to a webhook results
    in a status code != 200 from recipient service.
    """
    def __init__(self, message, status_code, response_body):
        super(WebhookError, self).__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class WebhookService(object):

    def get_subscription(self, subscription_id, session):
        """
        :param int subscription_id:
        :param sqlalchemy.orm.Session session:
        :rtype: WebhookSubscription
        """
        return session \
            .query(WebhookSubscription) \
            .filter(WebhookSubscription.id == subscription_id) \
            .one()

    def get_subscriptions(self, event, subject, session):
        """
        :param WebhookEvent event:
        :param str subject:
        :param sqlalchemy.orm.Session session:
        :rtype: list[WebhookSubscription]
        """
        return session \
            .query(WebhookSubscription) \
            .filter(WebhookSubscription.event == event) \
            .filter(WebhookSubscription.subject == subject) \
            .all()

    @atomic
    def subscribe(self, event, subject, url, secret, session):
        """
        :param WebhookEvent event:
        :param str subject:
        :param str url:
        :param str secret:
        :param sqlalchemy.orm.Session session:
        """
        session.add(WebhookSubscription(
            event=event,
            subject=subject,
            url=url,
            secret=secret,
        ))

    def publish(self, subscription, schema, request):
        body = schema.dump(request)

        hmac_header = 'sha256=' + b64encode(hmac.new(
            subscription.secret.encode(),
            json.dumps(body).encode(),
            sha256
        ).digest()).decode()

        headers = {
            HMAC_HEADER: hmac_header
        }

        logger.info(f'Invoking webhook: {subscription.event.value}', extra={
            'subject': subscription.subject,
            'event': subscription.event.value,
            'url': subscription.url,
            'request': str(body),
        })

        try:
            response = requests.post(
                url=subscription.url,
                json=body,
                headers=headers,
                verify=not DEBUG,
            )
        except:
            raise WebhookConnectionError('Failed to POST request to subscriber')

        if response.status_code != 200:
            raise WebhookError(
                'Invoking webhook resulted in status code != 200',
                status_code=response.status_code,
                response_body=str(response.content),
            )

    def on_ggo_received(self, subscription, ggo):
        """
        :param WebhookSubscription subscription:
        :param Ggo ggo:
        """
        self.publish(
            subscription=subscription,
            schema=md.class_schema(OnGgoReceivedRequest)(),
            request=OnGgoReceivedRequest(
                sub=subscription.subject,
                ggo=ggo,
            )
        )
