from django.core.urlresolvers import reverse
from django.db import models
from mock_django import mock_signal_receiver
from rest_framework import status, test

from nodeconductor.structure import signals
from nodeconductor.structure.models import Customer, CustomerRole, ProjectRole
from nodeconductor.structure.tests import factories, fixtures, models as test_models


class SuspendServiceTest(test.APITransactionTestCase):

    def setUp(self):
        self.user = factories.UserFactory()
        self.customer = factories.CustomerFactory(balance=-10)
        self.customer.add_user(self.user, CustomerRole.OWNER)

    def _get_url(self, view_name, **kwargs):
        return 'http://testserver' + reverse(view_name, kwargs=kwargs)

    def test_credit_customer(self):
        amount = 7.45
        customer = factories.CustomerFactory()

        with mock_signal_receiver(signals.customer_account_credited) as receiver:
            customer.credit_account(amount)

            receiver.assert_called_once_with(
                instance=customer,
                amount=amount,
                sender=Customer,
                signal=signals.customer_account_credited,
            )

            self.assertEqual(customer.balance, amount)


class ServiceResourcesCounterTest(test.APITransactionTestCase):
    """
    There's one shared service. Also there are 2 users each of which has one project.
    There's one VM in each project. Service counters for each user should equal 1.
    For staff user resource counter should equal 2.
    """
    def setUp(self):
        self.customer = factories.CustomerFactory()
        self.settings = factories.ServiceSettingsFactory(shared=True)
        self.service = factories.TestServiceFactory(customer=self.customer, settings=self.settings)

        self.user1 = factories.UserFactory()
        self.project1 = factories.ProjectFactory(customer=self.customer)
        self.project1.add_user(self.user1, ProjectRole.ADMINISTRATOR)
        self.spl1 = factories.TestServiceProjectLinkFactory(service=self.service, project=self.project1)
        self.vm1 = factories.TestNewInstanceFactory(service_project_link=self.spl1)

        self.user2 = factories.UserFactory()
        self.project2 = factories.ProjectFactory(customer=self.customer)
        self.project2.add_user(self.user2, ProjectRole.ADMINISTRATOR)
        self.spl2 = factories.TestServiceProjectLinkFactory(service=self.service, project=self.project2)
        self.vm2 = factories.TestNewInstanceFactory(service_project_link=self.spl2)

        self.service_url = factories.TestServiceFactory.get_url(self.service)

    def test_counters_for_shared_providers_should_be_filtered_by_user(self):
        self.client.force_authenticate(self.user1)
        response = self.client.get(self.service_url)
        self.assertEqual(1, response.data['resources_count'])

        self.client.force_authenticate(self.user2)
        response = self.client.get(self.service_url)
        self.assertEqual(1, response.data['resources_count'])

    def test_counters_are_not_filtered_for_staff(self):
        self.client.force_authenticate(factories.UserFactory(is_staff=True))
        response = self.client.get(self.service_url)
        self.assertEqual(2, response.data['resources_count'])


class UnlinkServiceTest(test.APITransactionTestCase):
    def test_when_service_is_unlinked_all_related_resources_are_unlinked_too(self):
        resource = factories.TestNewInstanceFactory()
        service = resource.service_project_link.service
        unlink_url = factories.TestServiceFactory.get_url(service, 'unlink')

        self.client.force_authenticate(factories.UserFactory(is_staff=True))
        response = self.client.post(unlink_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertRaises(models.ObjectDoesNotExist, service.refresh_from_db)

    def test_owner_cannot_unlink_service_with_shared_settings(self):
        fixture = fixtures.ServiceFixture()
        service_settings = factories.ServiceSettingsFactory(shared=True)
        service = test_models.TestService.objects.get(customer=fixture.customer, settings=service_settings)
        unlink_url = factories.TestServiceFactory.get_url(service, 'unlink')
        self.client.force_authenticate(fixture.owner)

        response = self.client.post(unlink_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(test_models.TestService.objects.filter(pk=service.pk).exists())
