import requests
import marshmallow_dataclass as md
from dataclasses import dataclass

from origin.db import atomic, inject_session
from origin.ggo import Ggo, MappedGgo

from .models import Subscription, Event
from ..settings import DEBUG


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

            try:
                response = requests.post(subscription.url, json=body, verify=not DEBUG)
            except:
                # TODO logging
                raise
                continue

            if response.status_code != 200:
                raise Exception('%s\n\n%s\n\n' % (body, response.content))

    def on_ggo_received(self, subject, ggo):
        """
        :param str subject:
        :param Ggo ggo:
        """
        return self.publish(
            event=Event.ON_GGO_RECEIVED,
            subject=subject,
            schema=md.class_schema(OnGgoReceivedRequest),
            request=OnGgoReceivedRequest(
                sub=subject,
                ggo=ggo,
            )
        )
