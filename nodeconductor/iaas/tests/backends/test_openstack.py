from __future__ import unicode_literals

import collections
import unittest

from django.test import TransactionTestCase
from keystoneclient import exceptions as keystone_exceptions
import mock

from nodeconductor.iaas.backend import CloudBackendError
from nodeconductor.iaas.backend.openstack import OpenStackBackend
from nodeconductor.iaas.models import Flavor, Instance, Image, FloatingIP
from nodeconductor.iaas.tests import factories

NovaFlavor = collections.namedtuple(
    'NovaFlavor',
    ['id', 'name', 'vcpus', 'ram', 'disk']
)

GlanceImageTuple = collections.namedtuple(
    'GlanceImage',
    ['id', 'is_public', 'deleted', 'min_ram', 'min_disk']
)


def GlanceImage(id, is_public, deleted, min_ram=0, min_disk=0):
    return GlanceImageTuple(id, is_public, deleted, min_ram, min_disk)


def next_unique_flavor_id():
    return factories.FlavorFactory.build().backend_id


def nc_flavor_to_nova_flavor(flavor):
    return NovaFlavor(
        id=flavor.backend_id,
        name=flavor.name,
        vcpus=flavor.cores,
        ram=flavor.ram,
        disk=flavor.disk / 1024,
    )


class OpenStackBackendConversionTest(unittest.TestCase):
    def setUp(self):
        self.backend = OpenStackBackend()

    def test_get_backend_ram_size_leaves_value_intact(self):
        core_ram = 4  # in MiB
        backend_ram = self.backend.get_backend_ram_size(core_ram)

        self.assertEqual(backend_ram, core_ram,
                         'Core ram and Backend ram are supposed be in the same units')

    def test_get_core_ram_size_leaves_value_intact(self):
        backend_ram = 4  # in MiB
        core_ram = self.backend.get_core_ram_size(backend_ram)

        self.assertEqual(core_ram, backend_ram,
                         'Core ram and Backend ram are supposed be in the same units')

    def test_get_backend_disk_size_converts_from_mebibytes_to_gibibytes(self):
        core_disk = 4096  # in MiB
        backend_disk = self.backend.get_backend_disk_size(core_disk)

        self.assertEqual(backend_disk, 4)

    def test_get_core_disk_size_converts_from_gibibytes_to_mebibytes(self):
        backend_disk = 4  # in GiB
        core_disk = self.backend.get_core_disk_size(backend_disk)

        self.assertEqual(core_disk, 4096)


class OpenStackBackendCloudAccountApiTest(unittest.TestCase):

    def setUp(self):
        self.keystone_client = mock.Mock()
        self.nova_client = mock.Mock()
        self.cloud_account = mock.Mock()
        self.backend = OpenStackBackend()

        self.backend.create_keystone_client = mock.Mock(return_value=self.keystone_client)
        self.backend.create_nova_client = mock.Mock(return_value=self.nova_client)

    def test_push_cloud_account_does_not_call_openstack_api(self):
        self.backend.push_cloud_account(self.cloud_account)

        self.assertFalse(self.backend.create_keystone_client.called, 'Keystone client should not have been created')
        self.assertFalse(self.backend.create_nova_client.called, 'Nova client should not have been created')

    def test_push_cloud_account_does_not_update_cloud_account(self):
        self.backend.push_cloud_account(self.cloud_account)

        self.assertFalse(self.cloud_account.save.called, 'Cloud account should not have been updated')


class OpenStackBackendMembershipApiTest(unittest.TestCase):
    def setUp(self):
        self.keystone_client = mock.Mock()
        self.nova_client = mock.Mock()
        self.neutron_client = mock.Mock()
        self.cloud_account = mock.Mock()
        self.cinder_client = mock.Mock()
        self.membership = mock.Mock()  # TODO: use real membership, not mocked and unite with test class below
        self.tenant = mock.Mock()

        # client methods:
        self.nova_quota = mock.Mock(cores=20, instances=10, ram=51200)
        self.nova_client.quotas.get = mock.Mock(return_value=self.nova_quota)
        self.cinder_quota = mock.Mock(gigabytes=1000)
        self.cinder_client.quotas.get = mock.Mock(return_value=self.cinder_quota)
        self.volumes = [mock.Mock(size=10 * i, id=i) for i in range(5)]
        self.snapshots = [mock.Mock(size=10 * i, id=i) for i in range(5)]
        self.flavors = [mock.Mock(ram=i, id=i, vcpus=i) for i in range(4)]
        self.instances = [mock.Mock(flavor={'id': i}) for i in range(2)]
        self.cinder_client.volume_snapshots.list = mock.Mock(return_value=self.snapshots)
        self.cinder_client.volumes.list = mock.Mock(return_value=self.volumes)
        self.nova_client.servers.list = mock.Mock(return_value=self.instances)
        self.nova_client.flavors.list = mock.Mock(return_value=self.flavors)

        # Mock low level non-AbstractCloudBackend api methods
        self.backend = OpenStackBackend()
        self.backend.create_admin_session = mock.Mock()
        self.backend.create_user_session = mock.Mock()
        self.backend.create_keystone_client = mock.Mock(return_value=self.keystone_client)
        self.backend.create_nova_client = mock.Mock(return_value=self.nova_client)
        self.backend.create_neutron_client = mock.Mock(return_value=self.neutron_client)
        self.backend.create_cinder_client = mock.Mock(return_value=self.cinder_client)
        self.backend.get_or_create_tenant = mock.Mock(return_value=self.tenant)
        self.backend.get_or_create_user = mock.Mock(return_value=('john', 'doe'))
        self.backend.get_or_create_network = mock.Mock()
        self.backend.ensure_user_is_tenant_admin = mock.Mock()
        self.backend.push_security_group = mock.Mock()
        self.backend.create_tenant_session = mock.Mock()
        self.backend.create_security_group = mock.Mock()
        self.backend.update_security_group = mock.Mock()
        self.backend.delete_security_group = mock.Mock()
        self.backend.push_security_group_rules = mock.Mock()
        self.backend.get_hypervisors_statistics = mock.Mock(return_value=[])

    def test_push_membership_synchronizes_user(self):
        self.backend.push_membership(self.membership)

        self.backend.get_or_create_user.assert_called_once_with(self.membership, self.keystone_client)

    def test_push_membership_synchronizes_tenant(self):
        self.backend.push_membership(self.membership)

        self.backend.get_or_create_tenant.assert_called_once_with(self.membership, self.keystone_client)

    def test_push_membership_synchronizes_network(self):
        self.backend.push_membership(self.membership)

        self.backend.get_or_create_network.assert_called_once_with(self.membership, self.neutron_client)

    def test_push_membership_synchronizes_users_role_in_tenant(self):
        self.backend.push_membership(self.membership)

        self.backend.get_or_create_user.ensure_user_is_tenant_admin('john', self.tenant, self.keystone_client)

    def test_push_membership_updates_membership_with_backend_data(self):
        self.backend.push_membership(self.membership)

        self.assertEquals(self.membership.username, 'john')
        self.assertEquals(self.membership.password, 'doe')
        self.assertEquals(self.membership.tenant_id, self.tenant.id)

        self.membership.save.assert_called_once_with()

    def test_push_membership_raises_on_openstack_api_error(self):
        self.backend.create_admin_session.side_effect = keystone_exceptions.AuthorizationFailure
        with self.assertRaises(CloudBackendError):
            self.backend.push_membership(self.membership)

    def test_get_resource_stats_gets_credentials_with_given_auth_url(self):
        auth_url = 'http://example.com/'
        self.backend.get_resource_stats(auth_url)
        self.backend.create_admin_session.assert_called_once_with(auth_url)

    def test_get_resource_stats_raises_openstack_api_error(self):
        self.backend.create_nova_client.side_effect = keystone_exceptions.AuthorizationFailure

        auth_url = 'http://example.com/'
        with self.assertRaises(CloudBackendError):
            self.backend.get_resource_stats(auth_url)

    def test_pull_quota_resource_initiates_quota_parameters(self):
        membership = factories.CloudProjectMembershipFactory(tenant_id='test_backend_id')
        # when
        self.backend.pull_resource_quota(membership)
        # then
        self.assertEqual(membership.quotas.get(name='ram').limit, self.nova_quota.ram)
        self.assertEqual(membership.quotas.get(name='max_instances').limit, self.nova_quota.instances)
        self.assertEqual(membership.quotas.get(name='vcpu').limit, self.nova_quota.cores)
        self.assertEqual(membership.quotas.get(name='storage').limit, self.cinder_quota.gigabytes * 1024)

    def test_pull_quota_resource_calls_clients_quotas_gets_methods_with_membership_tenant_id(self):
        membership = factories.CloudProjectMembershipFactory(tenant_id='test_backend_id')
         # when
        self.backend.pull_resource_quota(membership)
        # then
        self.nova_client.quotas.get.assert_called_once_with(tenant_id=membership.tenant_id)
        self.cinder_client.quotas.get.assert_called_once_with(tenant_id=membership.tenant_id)

    def test_pull_quota_resource_rewrite_old_resource_quota_data(self):
        membership = factories.CloudProjectMembershipFactory(tenant_id='test_backend_id')
        # when
        self.backend.pull_resource_quota(membership)
        # then
        self.assertEqual(membership.quotas.get(name='max_instances').limit, self.nova_quota.instances)

    def test_pull_quota_resource_usage_initiates_quota_parameters(self):
        membership = factories.CloudProjectMembershipFactory()
        # when
        self.backend.pull_resource_quota_usage(membership)
        # then
        instance_flavors = [f for f in self.flavors if f.id in [i.flavor['id'] for i in self.instances]]
        self.assertEqual(membership.quotas.get(name='ram').usage, sum([f.ram for f in instance_flavors]))
        self.assertEqual(membership.quotas.get(name='max_instances').usage, len(self.instances))
        self.assertEqual(membership.quotas.get(name='vcpu').usage, sum([f.vcpus for f in instance_flavors]))
        self.assertEqual(
            membership.quotas.get(name='storage').usage,
            sum([int(v.size * 1024) for v in self.volumes + self.snapshots]))

    def test_pull_quota_resource_usage_rewrite_old_resource_quota_usage_data(self):
        membership = factories.CloudProjectMembershipFactory()
        # when
        self.backend.pull_resource_quota_usage(membership)
        # then
        self.assertEqual(membership.quotas.get(name='max_instances').usage, len(self.instances))


class OpenStackBackendSecurityGroupsTest(TransactionTestCase):

    def setUp(self):
        self.keystone_client = mock.Mock()
        self.nova_client = mock.Mock()
        self.neutron_client = mock.Mock()
        self.cloud_account = mock.Mock()
        self.membership = factories.CloudProjectMembershipFactory()
        self.tenant = mock.Mock()

        # Mock low level non-AbstractCloudBackend api methods
        self.backend = OpenStackBackend()
        self.backend.create_admin_session = mock.Mock()
        self.backend.create_user_session = mock.Mock()
        self.backend.create_keystone_client = mock.Mock(return_value=self.keystone_client)
        self.backend.create_nova_client = mock.Mock(return_value=self.nova_client)
        self.backend.create_neutron_client = mock.Mock(return_value=self.neutron_client)
        self.backend.get_or_create_tenant = mock.Mock(return_value=self.tenant)
        self.backend.get_or_create_user = mock.Mock(return_value=('john', 'doe'))
        self.backend.get_or_create_network = mock.Mock()
        self.backend.ensure_user_is_tenant_admin = mock.Mock()
        self.backend.push_security_group = mock.Mock()
        self.backend.create_tenant_session = mock.Mock()
        self.backend.create_security_group = mock.Mock()
        self.backend.update_security_group = mock.Mock()
        self.backend.delete_security_group = mock.Mock()
        self.backend.push_security_group_rules = mock.Mock()

    def test_push_security_groups_creates_nonexisting_groups(self):
        group1 = factories.SecurityGroupFactory(cloud_project_membership=self.membership)
        group2 = factories.SecurityGroupFactory(cloud_project_membership=self.membership)
        self.nova_client.security_groups.list = mock.Mock(return_value=[])
        # when
        self.backend.push_security_groups(self.membership)
        # then
        self.backend.create_security_group.assert_any_call(group1, self.nova_client)
        self.backend.create_security_group.assert_any_call(group2, self.nova_client)

    def test_push_security_groups_updates_unsynchronized_groups(self):
        group1 = factories.SecurityGroupFactory(cloud_project_membership=self.membership, backend_id=1)
        group2 = mock.Mock()
        group2.name = 'group2'
        group2.id = 1
        self.nova_client.security_groups.list = mock.Mock(return_value=[group2])
        # when
        self.backend.push_security_groups(self.membership)
        # then
        self.backend.update_security_group.assert_any_call(group1, self.nova_client)

    def test_push_security_groups_deletes_nonexisting_groups(self):
        group1 = mock.Mock()
        group1.name = 'group1'
        group1.id = 1
        self.nova_client.security_groups.list = mock.Mock(return_value=[group1])
        # when
        self.backend.push_security_groups(self.membership)
        # then
        self.backend.delete_security_group.assert_any_call(str(group1.id), self.nova_client)

    def test_push_membership_security_groups_raises_cloud_backed_error_on_keystone_error(self):
        self.backend.create_tenant_session.side_effect = keystone_exceptions.AuthorizationFailure()
        with self.assertRaises(CloudBackendError):
            self.backend.push_security_groups(self.membership)


class OpenStackBackendFlavorApiTest(TransactionTestCase):
    def setUp(self):
        self.nova_client = mock.Mock()
        self.nova_client.flavors.findall.return_value = []

        self.cloud_account = factories.CloudFactory()
        self.flavors = factories.FlavorFactory.create_batch(2, cloud=self.cloud_account)

        # Mock low level non-AbstractCloudBackend api methods
        self.backend = OpenStackBackend()
        self.backend.create_admin_session = mock.Mock()
        self.backend.create_nova_client = mock.Mock(return_value=self.nova_client)

    # TODO: Test pull_flavors uses proper credentials for nova
    def test_pull_flavors_queries_only_public_flavors(self):
        self.backend.pull_flavors(self.cloud_account)

        self.nova_client.flavors.findall.assert_called_once_with(
            is_public=True
        )

    def test_pull_flavors_creates_flavors_missing_in_database(self):
        # Given
        new_flavor = NovaFlavor(next_unique_flavor_id(), 'id1', 3, 5, 8)

        self.nova_client.flavors.findall.return_value = [
            nc_flavor_to_nova_flavor(self.flavors[0]),
            nc_flavor_to_nova_flavor(self.flavors[1]),
            new_flavor,
        ]

        # When
        self.backend.pull_flavors(self.cloud_account)

        # Then
        try:
            stored_flavor = self.cloud_account.flavors.get(backend_id=new_flavor.id)

            self.assertEqual(stored_flavor.name, new_flavor.name)
            self.assertEqual(stored_flavor.cores, new_flavor.vcpus)
            self.assertEqual(stored_flavor.ram, new_flavor.ram)
            self.assertEqual(stored_flavor.disk, new_flavor.disk * 1024)
        except Flavor.DoesNotExist:
            self.fail('Flavor should have been created in the database')

    def test_pull_flavors_updates_matching_flavors(self):
        # Given
        def double_fields(flavor):
            return flavor._replace(
                name=flavor.name + 'foo',
                vcpus=flavor.vcpus * 2,
                ram=flavor.ram * 2,
                disk=flavor.disk * 2,
            )

        backend_flavors = [
            double_fields(nc_flavor_to_nova_flavor(self.flavors[0])),
            double_fields(nc_flavor_to_nova_flavor(self.flavors[1])),
        ]

        self.nova_client.flavors.findall.return_value = backend_flavors

        # When
        self.backend.pull_flavors(self.cloud_account)

        # Then
        for updated_flavor in backend_flavors:
            stored_flavor = self.cloud_account.flavors.get(backend_id=updated_flavor.id)

            self.assertEqual(stored_flavor.name, updated_flavor.name)
            self.assertEqual(stored_flavor.cores, updated_flavor.vcpus)
            self.assertEqual(stored_flavor.ram, updated_flavor.ram)
            self.assertEqual(stored_flavor.disk, updated_flavor.disk * 1024)

    def test_pull_flavors_deletes_flavors_missing_in_backend(self):
        # Given
        self.nova_client.flavors.findall.return_value = [
            nc_flavor_to_nova_flavor(self.flavors[0]),
        ]

        # When
        self.backend.pull_flavors(self.cloud_account)

        # Then
        is_present = self.cloud_account.flavors.filter(
            backend_id=self.flavors[1].backend_id).exists()

        self.assertFalse(is_present, 'Flavor should have been deleted from the database')


class OpenStackBackendFloatingIPTest(TransactionTestCase):

    def setUp(self):
        self.keystone_client = mock.Mock()
        self.nova_client = mock.Mock()
        self.neutron_client = mock.Mock()
        self.cloud_account = mock.Mock()
        self.membership = factories.CloudProjectMembershipFactory()
        self.tenant = mock.Mock()

        # Mock low level non-AbstractCloudBackend api methods
        self.backend = OpenStackBackend()
        self.backend.create_admin_session = mock.Mock()
        self.backend.create_user_session = mock.Mock()
        self.backend.create_keystone_client = mock.Mock(return_value=self.keystone_client)
        self.backend.create_nova_client = mock.Mock(return_value=self.nova_client)
        self.backend.create_neutron_client = mock.Mock(return_value=self.neutron_client)
        self.backend.get_or_create_tenant = mock.Mock(return_value=self.tenant)
        self.backend.get_or_create_user = mock.Mock(return_value=('john', 'doe'))
        self.backend.get_or_create_network = mock.Mock()
        self.backend.ensure_user_is_tenant_admin = mock.Mock()
        self.backend.create_tenant_session = mock.Mock()
        self.floating_ips = [
            {'status': 'ACTIVE', 'floating_ip_address': '10.7.201.163', 'id': '063795b7-23ac-4a0d-82f0-4326e73ee1bc', 'port_id': 'fakeport'},
            {'status': 'DOWN', 'floating_ip_address': '10.7.201.114', 'id': '063795b7-23ac-4a0d-82f0-432as73asdas', 'port_id': 'fakeport'},
            {'status': 'ACTIVE', 'floating_ip_address': '10.7.201.107', 'id': '063795b7-asds-aq34-3df4-23asdasddssc', 'port_id': 'fakeport'},
        ]
        self.backend.get_floating_ips = mock.Mock(return_value=self.floating_ips)

    def test_pull_floating_ips_deletes_staled_ips(self):
        staled_ip = factories.FloatingIPFactory(backend_id='qqqq', cloud_project_membership=self.membership)
        # when
        self.backend.pull_floating_ips(self.membership)
        # then
        self.assertFalse(FloatingIP.objects.filter(id=staled_ip.id).exists(), 'Staled floating ip should be deleted')

    def test_pull_floating_ips_creates_new_ips(self):
        # when
        self.backend.pull_floating_ips(self.membership)
        # then
        for ip in self.floating_ips:
            self.assertTrue(
                FloatingIP.objects.filter(backend_id=ip['id']).exists(), 'Unexisted floating ip should be created')
            self.assertEqual

    def test_pull_floating_ips_updates_existing_ips(self):
        backend_ip = self.floating_ips[0]
        nc_floating_ip = factories.FloatingIPFactory(
            backend_id=backend_ip['id'], cloud_project_membership=self.membership)
        # when
        self.backend.pull_floating_ips(self.membership)
        # then
        reread_ip = FloatingIP.objects.get(id=nc_floating_ip.id)
        backend_ip = self.floating_ips[0]
        self.assertEqual(reread_ip.address, backend_ip['floating_ip_address'])
        self.assertEqual(reread_ip.status, backend_ip['status'])
        self.assertEqual(reread_ip.backend_id, backend_ip['id'])


class OpenStackBackendImageApiTest(TransactionTestCase):
    def setUp(self):
        self.glance_client = mock.Mock()

        #  C
        #  ^
        #  |
        # (I0)
        #  |
        #  v
        #  T0          T1        T2
        #  ^           ^         ^
        #  | \         | \       |
        #  |  \        |  \      |
        #  |   \       |   \     |
        #  v    v      v    v    v
        #  TM0  TM1    TM2  TM3  TM4
        #

        self.cloud_account = factories.CloudFactory()
        self.templates = factories.TemplateFactory.create_batch(3)

        self.template_mappings = (
            factories.TemplateMappingFactory.create_batch(2, template=self.templates[0]) +
            factories.TemplateMappingFactory.create_batch(2, template=self.templates[1]) +
            factories.TemplateMappingFactory.create_batch(1, template=self.templates[2])
        )

        self.image = factories.ImageFactory(
            cloud=self.cloud_account,
            template=self.template_mappings[0].template,
            backend_id=self.template_mappings[0].backend_image_id,
        )

        # Mock low level non-AbstractCloudBackend api methods
        self.backend = OpenStackBackend()
        self.backend.create_admin_session = mock.Mock()
        self.backend.create_glance_client = mock.Mock(return_value=self.glance_client)

    def test_pulling_creates_images_for_all_matching_template_mappings(self):
        # Given
        matching_mapping1 = self.template_mappings[2]
        image_id = matching_mapping1.backend_image_id
        new_image = GlanceImage(image_id, is_public=True, deleted=False)

        # Make another mapping use the same backend id
        matching_mapping2 = self.template_mappings[4]
        matching_mapping2.backend_image_id = image_id
        matching_mapping2.save()

        self.glance_client.images.list.return_value = iter([
            new_image,
        ])

        # When
        self.backend.pull_images(self.cloud_account)

        # Then
        image_count = self.cloud_account.images.filter(
            backend_id=new_image.id,
        ).count()

        self.assertEqual(2, image_count,
                         'Two images should have been created')

        try:
            self.cloud_account.images.get(
                backend_id=matching_mapping1.backend_image_id,
                template=matching_mapping1.template,
            )
        except Image.DoesNotExist:
            self.fail('Image for the first matching template mapping'
                      ' should have been created')

        try:
            self.cloud_account.images.get(
                backend_id=matching_mapping2.backend_image_id,
                template=matching_mapping2.template,
            )
        except Image.DoesNotExist:
            self.fail('Image for the second matching template mapping'
                      ' should have been created')

    def test_pulling_doesnt_create_images_missing_in_database_if_template_mapping_doesnt_exist(self):
        # Given
        non_matching_image = GlanceImage('not-mapped-id', is_public=True, deleted=False)

        self.glance_client.images.list.return_value = iter([
            non_matching_image,
        ])

        # When
        self.backend.pull_images(self.cloud_account)

        # Then
        image_exists = self.cloud_account.images.filter(
            backend_id=non_matching_image.id,
        ).exists()
        self.assertFalse(image_exists, 'Image should not have been created in the database')

    def test_pulling_doesnt_create_images_for_non_public_backend_images(self):
        # Given
        matching_mapping = self.template_mappings[2]
        image_id = matching_mapping.backend_image_id
        new_image = GlanceImage(image_id, is_public=False, deleted=False)

        self.glance_client.images.list.return_value = iter([
            new_image,
        ])

        # When
        self.backend.pull_images(self.cloud_account)

        # Then
        image_exists = self.cloud_account.images.filter(
            backend_id=new_image.id,
        ).exists()
        self.assertFalse(image_exists, 'Image should not have been created in the database')

    def test_pulling_doesnt_create_images_for_deleted_backend_images(self):
        # Given
        matching_mapping = self.template_mappings[2]
        image_id = matching_mapping.backend_image_id
        new_image = GlanceImage(image_id, is_public=True, deleted=True)

        self.glance_client.images.list.return_value = iter([
            new_image,
        ])

        # When
        self.backend.pull_images(self.cloud_account)

        # Then
        image_exists = self.cloud_account.images.filter(
            backend_id=new_image.id,
        ).exists()
        self.assertFalse(image_exists, 'Image should not have been created in the database')

    def test_pulling_does_not_create_image_if_backend_image_ids_collide(self):
        # Given
        matching_mapping1 = self.template_mappings[2]
        new_image1 = GlanceImage(matching_mapping1.backend_image_id, is_public=True, deleted=False)

        # Make another mapping use the same backend id
        matching_mapping2 = self.template_mappings[3]
        new_image2 = GlanceImage(matching_mapping2.backend_image_id, is_public=True, deleted=False)

        self.glance_client.images.list.return_value = iter([
            new_image1,
            new_image2,
        ])

        # When
        self.backend.pull_images(self.cloud_account)

        # Then
        images_exist = self.cloud_account.images.filter(
            template=self.templates[1]
        ).exists()

        self.assertFalse(images_exist,
                         'No images should have been created')

    def test_pulling_deletes_existing_image_if_template_mapping_doesnt_exist(self):
        # Given

        non_matching_image = GlanceImage('not-mapped-id', is_public=True, deleted=False)

        self.glance_client.images.list.return_value = iter([
            non_matching_image,
        ])

        # When
        self.backend.pull_images(self.cloud_account)

        # Then
        matching_mapping = self.template_mappings[0]

        image_exists = self.cloud_account.images.filter(
            backend_id=matching_mapping.backend_image_id,
            template=matching_mapping.template,
        ).exists()

        self.assertFalse(image_exists, 'Image should have been deleted')

    def test_pulling_updates_existing_images_backend_id_if_template_mapping_changed(self):
        # Given

        # Simulate MO updating the mapping
        matching_mapping = self.template_mappings[0]
        image_id = 'new-id'
        matching_mapping.backend_image_id = image_id
        matching_mapping.save()

        existing_image = GlanceImage(image_id, is_public=True, deleted=False)

        self.glance_client.images.list.return_value = iter([
            existing_image,
        ])

        # When
        self.backend.pull_images(self.cloud_account)

        # Then
        try:
            self.cloud_account.images.get(
                backend_id=matching_mapping.backend_image_id,
                template=matching_mapping.template,
            )
        except Image.DoesNotExist:
            self.fail("Image's backend_id should have been updated")


class OpenStackBackendInstanceApiTest(TransactionTestCase):
    def setUp(self):
        self.nova_client = mock.Mock()
        self.nova_client.servers.list.return_value = []
        self.nova_client.servers.findall.return_value = []

        self.membership = factories.CloudProjectMembershipFactory()

        # Mock low level non-AbstractCloudBackend api methods
        self.backend = OpenStackBackend()
        self.backend.create_tenant_session = mock.Mock()
        self.backend.create_nova_client = mock.Mock(return_value=self.nova_client)

    # XXX: import only the 1st data volume, sort by device name

    # Backend query tests
    def test_pull_instances_filters_out_instances_booted_from_image(self):
        self.when()

        self.nova_client.servers.findall.assert_called_once_with(
            image='',
        )

    # Deletion tests
    def test_pull_instances_errs_stable_instances_missing_in_backend(self):
        # Given
        membership_params = self._get_membership_params()

        for state in Instance.States.STABLE_STATES:
            factories.InstanceFactory(state=state, **membership_params)

        self.when()

        # Then
        instances = Instance.objects.filter(**membership_params)

        self.assertTrue(all([i.state == Instance.States.ERRED for i in instances]),
                        'Instances should have been set to erred state')

    def test_pull_instances_doesnt_delete_unstable_instances_missing_in_backend(self):
        # Given
        membership_params = self._get_membership_params()

        for state in Instance.States.UNSTABLE_STATES:
            factories.InstanceFactory(state=state, **membership_params)

        # When
        self.when()

        # Then
        expected_instance_count = len(Instance.States.UNSTABLE_STATES)
        actual_instance_count = Instance.objects.filter(**membership_params).count()

        self.assertEqual(expected_instance_count, actual_instance_count,
                         'No instances should have been deleted from the database')

    # Helper methods
    def given_minimal_importable_instance(self):
        # Create a flavor
        flavor = NovaFlavor(next_unique_flavor_id(), 'id1', 3, 5, 8)

        # from novaclient.v1_1.servers import Server as NovaServer

        # Create a server
        # server = mock.Mock(spec_set=NovaServer)
        server = mock.Mock()
        server.id = 'server-uuid-1'
        server.name = 'hostname-1'
        server.flavor = {
            'id': flavor.id,
            'links': [
                {
                    'href': 'http://example.com/TENANT-ID-1/flavors/%s' % flavor.id,
                    'rel': 'bookmark',
                }
            ]
        }
        server.status = 'ACTIVE'
        server.image = ''

        # Mock volume fetches
        # Mock flavor fetches
        # Mock server fetches
        self.nova_client.servers.findall.return_value = [server]
        self.nova_client.servers.find.return_value = server

    def when(self):
        self.backend.pull_instances(self.membership)

    def _get_membership_params(self):
        return dict(
            # XXX: Should we introduce ProjectMember mixin?
            cloud_project_membership=self.membership,
        )


class OpenStackBackendHelperApiTest(unittest.TestCase):
    def setUp(self):
        self.keystone_client = mock.Mock()
        self.nova_client = mock.Mock()

        self.membership = mock.Mock()
        self.membership.project.uuid.hex = 'project_uuid'
        self.membership.project.name = 'project_name'
        self.membership.project.description = 'project_description'

        self.backend = OpenStackBackend()

    # get_or_create_tenant tests
    def test_get_or_create_tenant_creates_tenant_with_proper_arguments(self):
        created_tenant = object()

        self.keystone_client.tenants.create.return_value = created_tenant
        tenant = self.backend.get_or_create_tenant(self.membership, self.keystone_client)

        self.keystone_client.tenants.create.assert_called_once_with(
            tenant_name='nc-project_uuid',
            description='project_description',
        )

        self.assertEquals(tenant, created_tenant, 'Created tenant not returned')

    def test_get_or_create_tenant_looks_up_existing_tenant_if_creation_fails_due_to_conflict(self):
        existing_tenant = object()

        self.keystone_client.tenants.create.side_effect = keystone_exceptions.Conflict
        self.keystone_client.tenants.find.return_value = existing_tenant

        tenant = self.backend.get_or_create_tenant(self.membership, self.keystone_client)

        self.keystone_client.tenants.find.assert_called_once_with(
            name='nc-project_uuid',
        )

        self.assertEquals(tenant, existing_tenant, 'Looked up tenant not returned')

    def test_get_or_create_tenant_raises_if_both_creation_and_lookup_failed(self):
        self.keystone_client.tenants.create.side_effect = keystone_exceptions.Conflict
        self.keystone_client.tenants.find.side_effect = keystone_exceptions.NotFound

        with self.assertRaises(keystone_exceptions.ClientException):
            self.backend.get_or_create_tenant(self.membership, self.keystone_client)

    # get_or_create_user tests
    def test_get_or_create_user_creates_user_if_membership_was_never_synchronized_before(self):
        # This is a brand new membership that was never synchronized
        self.membership.username = ''

        username, password = self.backend.get_or_create_user(self.membership, self.keystone_client)

        self.assertEqual(self.keystone_client.users.create.call_count, 1,
                         'tenant.users.create() must be called exactly once')

        call_kwargs = self.keystone_client.users.create.call_args[1]
        call_username = call_kwargs.get('name')
        call_password = call_kwargs.get('password')

        # Check created username matches returned ones
        self.assertEqual(
            (call_username, call_password), (username, password),
            'Credentials used for account creation do not match the ones returned')

        self.assertTrue(
            username.endswith('-{0}'.format('project_name')),
            'Username should contain project name'
        )
        self.assertTrue(password, 'Password should not be empty')

    def test_get_or_create_user_returns_existing_credentials_if_they_are_valid(self):
        # This is a membership that was synchronized before
        self.membership.username = 'my_user'
        self.membership.password = 'my_pass'

        # Pretend we can log in using existing credentials
        self.backend.create_user_session = mock.Mock()

        username, password = self.backend.get_or_create_user(self.membership, self.keystone_client)

        self.assertFalse(self.keystone_client.called,
                         'Keystone must not be accessed')

        self.assertEqual(
            ('my_user', 'my_pass'), (username, password),
            'Credentials do not match the ones stored in membership')

    def test_get_or_create_user_creates_user_with_the_username_if_existing_credentials_are_invalid(self):
        # This is a membership that was synchronized before...
        self.membership.username = 'my_user-project_name'
        self.membership.password = 'my_pass'

        # ... but they became stale
        self.backend.create_user_session = mock.Mock(side_effect=keystone_exceptions.AuthorizationFailure)

        username, password = self.backend.get_or_create_user(self.membership, self.keystone_client)

        self.assertEqual(self.keystone_client.users.create.call_count, 1,
                         'tenant.users.create() must be called exactly once')

        call_kwargs = self.keystone_client.users.create.call_args[1]
        call_username = call_kwargs.get('name')
        call_password = call_kwargs.get('password')

        # Check created username matches returned ones
        self.assertEqual(
            call_username, 'my_user-project_name',
            'Existing username should have been used')

        self.assertEqual(
            (call_username, call_password), (username, password),
            'Credentials used for account creation do not match the ones returned')

        self.assertTrue(
            username.endswith('-{0}'.format('project_name')),
            'Username should contain project name'
        )
        self.assertTrue(password, 'Password should not be empty')
