from __future__ import unicode_literals

from django.core.urlresolvers import reverse
import factory

from nodeconductor.logging import models
from nodeconductor.logging import elasticsearch_dummy_client
# Dependency from `structure` application exists only in tests
from nodeconductor.structure.tests import factories as structure_factories


class EventFactory(object):
    """
    Event factory that provides default data for events and adds created events to elasticsearch dummy client.

    Created event fields can be accessible via .fields attribute of created event.
    """

    def __init__(self, **kwargs):
        self.create(**kwargs)
        self.save()

    def create(self, **kwargs):
        """
        Creates event fields values.

        If field is in kwargs - value from kwargs will be used for this field,
        otherwise - default value will be used for field.
        """
        self.fields = {
            '@timestamp': '2015-04-19T16:25:45.376+04:00',
            '@version': 1,
            'cloud_account_name': 'test_cloud_account_name',
            'cloud_account_uuid': 'test_cloud_account_uuid',
            'customer_abbreviation': 'TCAN',
            'customer_contact_details': 'test details',
            'customer_name': 'Test cusomter',
            'customer_uuid': 'test_customer_uuid',
            'event_type': 'test_event_type',
            'host': 'example.com',
            'importance': 'high',
            'importance_code': 30,
            'levelname': 'WARNING',
            'logger': 'nodeconductor.test',
            'message': 'Test message',
            'project_group_name': 'test_group_name',
            'project_group_uuid': 'test_group_uuid',
            'project_name': 'test_project',
            'project_uuid': 'test_project_uuid',
            'tags': ['_jsonparsefailure'],
            'type': 'gcloud-event',
            'user_uuid': 'test_user_uuid',
        }
        for key, value in kwargs.items():
            self.fields[key] = value

    def save(self):
        """ Add event to elasticsearch dummy client events """
        elasticsearch_dummy_client.DUMMY_EVENTS.append(self.fields)

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('event-list')


class AlertFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Alert

    message = factory.Sequence(lambda i: 'message#%s' % i)
    alert_type = factory.Iterator(['first_alert', 'second_alert', 'third_alert', 'fourth_alert'])
    severity = factory.Iterator([
        models.Alert.SeverityChoices.DEBUG, models.Alert.SeverityChoices.INFO,
        models.Alert.SeverityChoices.WARNING, models.Alert.SeverityChoices.ERROR])
    context = {'test': 'test'}
    scope = factory.SubFactory(structure_factories.CustomerFactory)

    @classmethod
    def get_list_url(self):
        return 'http://testserver' + reverse('alert-list')

    @classmethod
    def get_stats_url(self):
        return 'http://testserver' + reverse('alert-stat')
