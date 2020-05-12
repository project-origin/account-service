import requests
import marshmallow_dataclass as md
from dataclasses import dataclass

from origin import logger
from origin.settings import DEBUG
from origin.db import atomic, inject_session
from origin.ggo import Ggo, MappedGgo

from .models import Subscription, Event


@dataclass
class OnGgoReceivedRequest:
    sub: str
    ggo: MappedGgo


class WebhookService(object):

    @atomic
    def subscribe(self, event, subject, url, session):
        """
        :param Event event:
        :param str subject:
        :param str url:
        :param Session session:
        """
        session.add(Subscription(
            event=event,
            subject=subject,
            url=url,
        ))

    @inject_session
    def publish(self, event, subject, schema, request, session):
        """
        :param Event event:
        :param str subject:
        :param Schema schema:
        :param obj request:
        :param Session session:
        """
        filters = (
            Subscription.event == event,
            Subscription.subject == subject,
        )

        subscriptions = session.query(Subscription) \
            .filter(*filters) \
            .all()

        for subscription in subscriptions:
            body = schema().dump(request)

            logger.info(f'Invoking webhook: {event.value}', extra={
                'subject': subject,
                'event': event.value,
                'url': subscription.url,
                'request': str(body),
            })

            try:
                response = requests.post(subscription.url, json=body, verify=not DEBUG)
            except:
                logger.exception(f'Failed to invoke webhook: {event.value}', extra={
                    'subject': subject,
                    'event': event.value,
                    'url': subscription.url,
                    'request': str(body),
                })
                continue

            if response.status_code != 200:
                logger.error('Invoking webhook resulted in status code != 200', extra={
                    'subject': subject,
                    'event': event.value,
                    'url': subscription.url,
                    'request': str(body),
                    'response_status_code': response.status_code,
                    'response_body': response.content,
                })

    def on_ggo_received(self, subject, ggo):
        """
        :param str subject:
        :param Ggo ggo:
        """
        with logger.tracer.span('Invoking webhook: OnGgoReceived'):
            return self.publish(
                event=Event.ON_GGO_RECEIVED,
                subject=subject,
                schema=md.class_schema(OnGgoReceivedRequest),
                request=OnGgoReceivedRequest(
                    sub=subject,
                    ggo=ggo,
                )
            )
