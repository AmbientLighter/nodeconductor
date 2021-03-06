from django.test import TestCase

from nodeconductor.structure.tests import factories
from nodeconductor.structure.tests import models as test_models


class ServiceSettingsSignalsTest(TestCase):

    def setUp(self):
        self.shared_service_settings = factories.ServiceSettingsFactory(shared=True)

    def test_shared_service_is_created_for_new_customer(self):
        customer = factories.CustomerFactory()

        self.assertTrue(test_models.TestService.objects.filter(
            customer=customer, settings=self.shared_service_settings, available_for_all=True).exists())


class ServiceProjectLinkSignalsTest(TestCase):

    def test_new_project_connects_to_available_services_of_customer(self):
        customer = factories.CustomerFactory()
        service = self.create_service(customer, available_for_all=True)

        other_customer = factories.CustomerFactory()
        other_service = self.create_service(other_customer, available_for_all=True)

        # Act
        project = factories.ProjectFactory(customer=customer)

        # Assert
        self.assertTrue(self.link_exists(project, service))
        self.assertFalse(self.link_exists(project, other_service))

    def test_if_service_became_available_it_connects_to_all_projects_of_customer(self):
        customer = factories.CustomerFactory()
        service = self.create_service(customer, available_for_all=False)
        project = factories.ProjectFactory(customer=customer)

        other_customer = factories.CustomerFactory()
        other_project = factories.ProjectFactory(customer=other_customer)

        # Act
        service.available_for_all = True
        service.save()

        # Assert
        self.assertTrue(self.link_exists(project, service))
        self.assertFalse(self.link_exists(other_project, service))

    def create_service(self, customer, available_for_all):
        service_settings = factories.ServiceSettingsFactory(shared=False)
        return test_models.TestService.objects.create(customer=customer,
                                                      settings=service_settings,
                                                      available_for_all=available_for_all)

    def link_exists(self, project, service):
        return test_models.TestServiceProjectLink.objects.filter(
            project=project, service=service).exists()
