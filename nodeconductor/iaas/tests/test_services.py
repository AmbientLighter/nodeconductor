from decimal import Decimal
from django.core.urlresolvers import reverse
from rest_framework import test, status

from nodeconductor.core.tests import helpers
from nodeconductor.iaas import models
from nodeconductor.iaas.tests import factories
from nodeconductor.structure import models as structure_models
from nodeconductor.structure.tests import factories as structure_factories


def _get_service_url(service):
    return 'http://testserver' + reverse('service-detail', kwargs={'uuid': service.uuid})


def _get_service_list_url():
    return 'http://testserver' + reverse('service-list')


def _service_to_dict(service):
    project_groups = []
    for project_group in service.cloud_project_membership.project.project_groups.all():
        project_groups.append(
            {
                'url': 'http://testserver' + reverse('projectgroup-detail', kwargs={'uuid': str(project_group.uuid)}),
                'uuid': project_group.uuid.hex,
                'name': project_group.name,
            })
    return {
        'url': _get_service_url(service),
        'uuid': service.uuid.hex,
        'state': service.get_state_display(),
        'project_name': service.cloud_project_membership.project.name,
        'hostname': service.hostname,
        'template_name': service.template.name,
        'customer_name': service.cloud_project_membership.project.customer.name,
        'customer_native_name': service.cloud_project_membership.project.customer.native_name,
        'customer_abbreviation': service.cloud_project_membership.project.customer.abbreviation,
        'project_groups': project_groups,
        'actual_sla': Decimal('99.9'),
        'agreed_sla': service.agreed_sla,
        'service_type': 'IaaS',
        'access_information': [service.external_ips],
    }


class ServicesListRetrieveTest(test.APISimpleTestCase):

    def setUp(self):
        self.staff = structure_factories.UserFactory(is_staff=True)
        self.customer = structure_factories.CustomerFactory()
        self.owner = structure_factories.UserFactory()
        self.customer.add_user(self.owner, structure_models.CustomerRole.OWNER)

        self.manager = structure_factories.UserFactory()
        self.manager_project = structure_factories.ProjectFactory(customer=self.customer)
        self.manager_project.add_user(self.manager, structure_models.ProjectRole.MANAGER)
        self.manager_project.project_groups.add(structure_factories.ProjectGroupFactory())

        self.group_manager = structure_factories.UserFactory()
        self.group_manager_project = structure_factories.ProjectFactory(customer=self.customer)
        project_group = structure_factories.ProjectGroupFactory()
        self.group_manager_project.project_groups.add(project_group)
        project_group.add_user(self.group_manager, structure_models.ProjectGroupRole.MANAGER)

        models.Instance.objects.all().delete()
        self.manager_instance = factories.InstanceFactory(
            cloud_project_membership__project=self.manager_project)
        factories.InstanceSlaHistoryFactory(instance=self.manager_instance, period='2015')

        self.group_manager_instance = factories.InstanceFactory(
            cloud_project_membership__project=self.group_manager_project)
        factories.InstanceSlaHistoryFactory(instance=self.group_manager_instance, period='2015')

        self.other_instance = factories.InstanceFactory()
        factories.InstanceSlaHistoryFactory(instance=self.other_instance, period='2015')

    def test_manager_can_list_only_services_from_his_projects(self):
        self.client.force_authenticate(self.manager)
        response = self.client.get(_get_service_list_url(), data={'period': '2015'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1, 'Manager can view more(or less) instances than expected')
        self.assertEqual(
            response.data[0]['url'], _get_service_url(self.manager_instance),
            'Manager can view instance not from his project')

    def test_group_manager_can_list_only_services_from_his_projects(self):
        self.client.force_authenticate(self.group_manager)
        response = self.client.get(_get_service_list_url(), data={'period': '2015'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1, 'Group manager can view more(or less) instances than expected')
        self.assertEqual(
            response.data[0]['url'], _get_service_url(self.group_manager_instance),
            'Manager can view instance not from his project')

    def test_staff_can_list_all_services(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get(_get_service_list_url(), data={'period': '2015'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3, 'Manager can view more(or less) instances than expected')
        self.assertItemsEqual(
            [d['url'] for d in response.data],
            [
                _get_service_url(self.manager_instance),
                _get_service_url(self.other_instance),
                _get_service_url(self.group_manager_instance)
            ]
        )

    def test_service_api_returns_expected_fields(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get(_get_service_url(self.manager_instance), data={'period': '2015'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertItemsEqual(
            response.data.keys(), _service_to_dict(self.manager_instance).keys(),
            'Service api returns more(or less) fields than expected')
        for key, value in _service_to_dict(self.manager_instance).iteritems():
            self.assertEqual(response.data[key], value,
                             'Service api returns wrong value for field %s: %s != %s' % (key, value, response.data[key]))


class PermissionsTest(helpers.PermissionsTest):

    def setUp(self):
        self.staff = structure_factories.UserFactory(is_staff=True)
        self.customer = structure_factories.CustomerFactory()
        self.owner = structure_factories.UserFactory()
        self.customer.add_user(self.owner, structure_models.CustomerRole.OWNER)

        self.manager = structure_factories.UserFactory(username='manager')
        self.admin = structure_factories.UserFactory(username='admin')
        self.project = structure_factories.ProjectFactory(customer=self.customer)
        self.project.add_user(self.manager, structure_models.ProjectRole.MANAGER)
        self.project.add_user(self.admin, structure_models.ProjectRole.ADMINISTRATOR)
        project_group = structure_factories.ProjectGroupFactory()
        self.project.project_groups.add(project_group)

        self.group_manager = structure_factories.UserFactory(username='group_manager')
        project_group.add_user(self.group_manager, structure_models.ProjectGroupRole.MANAGER)

        models.Instance.objects.all().delete()
        self.instance = factories.InstanceFactory(cloud_project_membership__project=self.project)
        factories.InstanceSlaHistoryFactory(instance=self.instance, period='2015')
        self.other_instance = factories.InstanceFactory()
        factories.InstanceSlaHistoryFactory(instance=self.other_instance, period='2015')

    def get_urls_configs(self):
        return [
            {'url': _get_service_url(self.instance), 'method': 'GET', 'data': {'period': '2015'}},
            {'url': _get_service_list_url(), 'method': 'GET', 'data': {'period': '2015'}},
            {'url': _get_service_url(self.other_instance), 'method': 'GET', 'data': {'period': '2015'}}]

    def get_users_with_permission(self, url, method):
        if url == _get_service_url(self.other_instance):
            return [self.staff]
        return [self.staff, self.manager, self.group_manager, self.admin]

    def get_users_without_permissions(self, url, method):
        if url == _get_service_url(self.other_instance):
            return [self.manager, self.group_manager, self.admin]
        return []
