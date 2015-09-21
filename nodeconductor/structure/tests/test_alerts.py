import factory
from rest_framework import test, status

from nodeconductor.logging.models import Alert
from nodeconductor.logging.tests.factories import AlertFactory
from nodeconductor.structure import SupportedServices
from nodeconductor.structure.models import CustomerRole
from nodeconductor.structure.tests import factories


class FilterAlertsByAggregateTest(test.APITransactionTestCase):

    def setUp(self):
        self.users = []
        self.customers = []
        self.projects = []

        self.project_alerts = []
        self.customer_alerts = []

        for i in range(2):
            customer = factories.CustomerFactory()
            user = factories.UserFactory()
            customer.add_user(user, CustomerRole.OWNER)

            project = factories.ProjectFactory(customer=customer)
            resource = self.create_resource(customer, project)
            spl = resource.service_project_link
            service = spl.service

            project_alerts = (
                AlertFactory(scope=project),
                AlertFactory(scope=resource),
                AlertFactory(scope=spl),
                AlertFactory(scope=service)
            )

            customer_alerts = project_alerts + (AlertFactory(scope=customer),)

            self.users.append(user)
            self.customers.append(customer)
            self.projects.append(project)

            self.project_alerts.append(project_alerts)
            self.customer_alerts.append(customer_alerts)

        Alert.objects.exclude(pk__in=[alert.pk for alerts in self.customer_alerts for alert in alerts]).delete()

    def test_alert_can_be_filtered_by_customer(self):
        for user, customer, alerts in zip(self.users, self.customers, self.customer_alerts):
            self.client.force_authenticate(user)
            query = {
                'aggregate': 'customer',
                'uuid': customer.uuid.hex
            }

            response = self.client.get(AlertFactory.get_list_url(), data=query)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            expected = set(alert.uuid.hex for alert in alerts)
            actual = set(alert['uuid'] for alert in response.data)
            self.assertEqual(expected, actual)

    def test_alert_can_be_filtered_by_project(self):
        for user, project, alerts in zip(self.users, self.projects, self.project_alerts):
            self.client.force_authenticate(user)
            query = {
                'aggregate': 'project',
                'uuid': project.uuid.hex
            }

            response = self.client.get(AlertFactory.get_list_url(), data=query)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            expected = set(alert.uuid.hex for alert in alerts)
            actual = set(alert['uuid'] for alert in response.data)
            self.assertEqual(expected, actual)

    def create_resource(self, customer, project):
        service_type, models = SupportedServices.get_service_models().items()[0]

        class ServiceFactory(factory.DjangoModelFactory):
            class Meta(object):
                model = models['service']

        class ServiceProjectLinkFactory(factory.DjangoModelFactory):
            class Meta(object):
                model = models['service_project_link']

        class ResourceFactory(factory.DjangoModelFactory):
            class Meta(object):
                model = models['resources'][0]

        settings = factories.ServiceSettingsFactory(customer=customer, type=service_type)
        service = ServiceFactory(customer=customer, settings=settings)
        spl = ServiceProjectLinkFactory(service=service, project=project)
        resource = ResourceFactory(service_project_link=spl)
        return resource
