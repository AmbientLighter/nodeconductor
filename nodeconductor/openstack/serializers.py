from rest_framework import serializers

from django.db import transaction
from django.db.models import Max
from netaddr import IPNetwork

from nodeconductor.core.fields import MappedChoiceField
from nodeconductor.core import models as core_models
from nodeconductor.core import serializers as core_serializers
from nodeconductor.quotas import serializers as quotas_serializers
from nodeconductor.structure import serializers as structure_serializers
from nodeconductor.structure import SupportedServices
from nodeconductor.openstack.backend import OpenStackBackendError
from nodeconductor.openstack import models


class ServiceSerializer(structure_serializers.BaseServiceSerializer):

    SERVICE_TYPE = SupportedServices.Types.OpenStack
    SERVICE_ACCOUNT_FIELDS = {
        'backend_url': 'Keystone auth URL (e.g. http://keystone.example.com:5000/v2.0)',
        'username': 'Administrative user',
        'password': '',
    }
    SERVICE_ACCOUNT_EXTRA_FIELDS = {
        'tenant_name': 'Administrative tenant (default: "admin")',
        'availability_zone': 'Default availability zone for provisioned Instances',
        'cpu_overcommit_ratio': '(default: 1)',
    }

    class Meta(structure_serializers.BaseServiceSerializer.Meta):
        model = models.OpenStackService
        view_name = 'openstack-detail'


class FlavorSerializer(structure_serializers.BasePropertySerializer):

    SERVICE_TYPE = SupportedServices.Types.OpenStack

    class Meta(object):
        model = models.Flavor
        view_name = 'openstack-flavor-detail'
        fields = ('url', 'uuid', 'name', 'cores', 'ram', 'disk')
        extra_kwargs = {
            'url': {'lookup_field': 'uuid'},
        }


class ImageSerializer(structure_serializers.BasePropertySerializer):

    SERVICE_TYPE = SupportedServices.Types.OpenStack

    class Meta(object):
        model = models.Image
        view_name = 'openstack-image-detail'
        fields = ('url', 'uuid', 'name', 'min_disk', 'min_ram')
        extra_kwargs = {
            'url': {'lookup_field': 'uuid'},
        }


class ServiceProjectLinkSerializer(structure_serializers.BaseServiceProjectLinkSerializer):

    quotas = quotas_serializers.QuotaSerializer(many=True, read_only=True)

    class Meta(structure_serializers.BaseServiceProjectLinkSerializer.Meta):
        model = models.OpenStackServiceProjectLink
        view_name = 'openstack-spl-detail'
        fields = structure_serializers.BaseServiceProjectLinkSerializer.Meta.fields + (
            'quotas', 'tenant_id', 'external_network_id', 'internal_network_id'
        )
        read_only_fields = ('tenant_id', 'external_network_id', 'internal_network_id')
        extra_kwargs = {
            'service': {'lookup_field': 'uuid', 'view_name': 'openstack-detail'},
        }


class ServiceProjectLinkQuotaSerializer(serializers.Serializer):
    instances = serializers.IntegerField(min_value=1, required=False)
    ram = serializers.IntegerField(min_value=1, required=False)
    vcpu = serializers.IntegerField(min_value=1, required=False)
    storage = serializers.IntegerField(min_value=1, required=False)
    security_group_count = serializers.IntegerField(min_value=1, required=False)
    security_group_rule_count = serializers.IntegerField(min_value=1, required=False)


class NestedServiceProjectLinkSerializer(structure_serializers.PermissionFieldFilteringMixin,
                                         core_serializers.AugmentedSerializerMixin,
                                         core_serializers.HyperlinkedRelatedModelSerializer):

    quotas = quotas_serializers.QuotaSerializer(many=True, read_only=True)
    state = MappedChoiceField(
        choices=[(v, k) for k, v in core_models.SynchronizationStates.CHOICES],
        choice_mappings={v: k for k, v in core_models.SynchronizationStates.CHOICES},
        read_only=True,
    )

    class Meta(object):
        model = models.OpenStackServiceProjectLink
        fields = (
            'url',
            'project', 'project_name', 'project_uuid',
            'service', 'service_name', 'service_uuid',
            'quotas',
            'state',
        )
        view_name = 'openstack-spl-detail'
        extra_kwargs = {
            'service': {'lookup_field': 'uuid', 'view_name': 'openstack-detail'},
            'project': {'lookup_field': 'uuid'},
        }

    def run_validators(self, value):
        # No need to validate any fields except 'url' that is validated in to_internal_value method
        pass

    def get_filtered_field_names(self):
        return 'project', 'service'

    def get_related_paths(self):
        return 'project', 'service'


class NestedSecurityGroupRuleSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.SecurityGroupRule
        fields = ('id', 'protocol', 'from_port', 'to_port', 'cidr')

    def to_internal_value(self, data):
        # Return exist security group as internal value if id is provided
        if 'id' in data:
            try:
                return models.SecurityGroupRule.objects.get(id=data['id'])
            except models.SecurityGroup:
                raise serializers.ValidationError('Security group with id %s does not exist' % data['id'])
        else:
            internal_data = super(NestedSecurityGroupRuleSerializer, self).to_internal_value(data)
            return models.SecurityGroupRule(**internal_data)


class ExternalNetworkSerializer(serializers.Serializer):
    vlan_id = serializers.CharField(required=False)
    vxlan_id = serializers.CharField(required=False)
    network_ip = core_serializers.IPAddressField()
    network_prefix = serializers.IntegerField(min_value=0, max_value=32)
    ips_count = serializers.IntegerField(min_value=1, required=False)

    def validate(self, attrs):
        vlan_id = attrs.get('vlan_id')
        vxlan_id = attrs.get('vxlan_id')

        if vlan_id is None and vxlan_id is None:
            raise serializers.ValidationError("VLAN or VXLAN ID should be provided.")
        elif vlan_id and vxlan_id:
            raise serializers.ValidationError("VLAN and VXLAN networks cannot be created simultaneously.")

        ips_count = attrs.get('ips_count')
        if ips_count is None:
            return attrs

        network_ip = attrs.get('network_ip')
        network_prefix = attrs.get('network_prefix')

        cidr = IPNetwork(network_ip)
        cidr.prefixlen = network_prefix

        # subtract router and broadcast IPs
        if cidr.size < ips_count - 2:
            raise serializers.ValidationError("Not enough Floating IP Addresses available.")

        return attrs


class AssignFloatingIpSerializer(serializers.Serializer):
    floating_ip_uuid = serializers.CharField()

    def __init__(self, instance, *args, **kwargs):
        self.assigned_instance = instance
        super(AssignFloatingIpSerializer, self).__init__(*args, **kwargs)

    def validate(self, attrs):
        ip_uuid = attrs.get('floating_ip_uuid')

        try:
            floating_ip = models.FloatingIP.objects.get(uuid=ip_uuid)
        except models.FloatingIP.DoesNotExist:
            raise serializers.ValidationError("Floating IP does not exist.")

        if floating_ip.status == 'ACTIVE':
            raise serializers.ValidationError("Floating IP status must be DOWN.")
        elif floating_ip.cloud_project_membership != self.assigned_instance.cloud_project_membership:
            raise serializers.ValidationError("Floating IP must belong to same cloud project membership.")

        return attrs


class FloatingIPSerializer(serializers.HyperlinkedModelSerializer):
    service_project_link = NestedServiceProjectLinkSerializer(read_only=True)

    class Meta:
        model = models.FloatingIP
        fields = ('url', 'uuid', 'status', 'address',
                  'service_project_link', 'backend_id', 'backend_network_id')
        extra_kwargs = {
            'url': {'lookup_field': 'uuid'},
        }
        view_name = 'openstack-fip-detail'


class SecurityGroupSerializer(core_serializers.AugmentedSerializerMixin,
                              serializers.HyperlinkedModelSerializer):

    state = MappedChoiceField(
        choices=[(v, k) for k, v in core_models.SynchronizationStates.CHOICES],
        choice_mappings={v: k for k, v in core_models.SynchronizationStates.CHOICES},
        read_only=True,
    )
    rules = NestedSecurityGroupRuleSerializer(many=True)
    service_project_link = NestedServiceProjectLinkSerializer(
        queryset=models.OpenStackServiceProjectLink.objects.all())

    class Meta(object):
        model = models.SecurityGroup
        fields = ('url', 'uuid', 'state', 'name', 'description', 'rules', 'service_project_link')
        read_only_fields = ('url', 'uuid')
        extra_kwargs = {
            'url': {'lookup_field': 'uuid'},
            'service_project_link': {'view_name': 'openstack-spl-detail'}
        }
        view_name = 'openstack-sgp-detail'
        protected_fields = ('service_project_link',)

    def validate(self, attrs):
        if self.instance is None:
            # Check security groups quotas on creation
            service_project_link = attrs.get('service_project_link')
            security_group_count_quota = service_project_link.quotas.get(name='security_group_count')
            if security_group_count_quota.is_exceeded(delta=1):
                raise serializers.ValidationError('Can not create new security group - amount quota exceeded')
            security_group_rule_count_quota = service_project_link.quotas.get(name='security_group_rule_count')
            if security_group_rule_count_quota.is_exceeded(delta=len(attrs.get('rules', []))):
                raise serializers.ValidationError('Can not create new security group - rules amount quota exceeded')
        else:
            # Check security_groups quotas on update
            service_project_link = self.instance.service_project_link
            new_rules_count = len(attrs.get('rules', [])) - self.instance.rules.count()
            if new_rules_count > 0:
                security_group_rule_count_quota = service_project_link.quotas.get(name='security_group_rule_count')
                if security_group_rule_count_quota.is_exceeded(delta=new_rules_count):
                    raise serializers.ValidationError(
                        'Can not update new security group rules - rules amount quota exceeded')

        return attrs

    def validate_rules(self, value):
        for rule in value:
            rule.full_clean(exclude=['security_group'])
            if rule.id is not None and self.instance is None:
                raise serializers.ValidationError('Cannot add existed rule with id %s to new security group' % rule.id)
            elif rule.id is not None and self.instance is not None and rule.security_group != self.instance:
                raise serializers.ValidationError('Cannot add rule with id {} to group {} - it already belongs to '
                                                  'other group' % (rule.id, self.isntance.name))
        return value

    def create(self, validated_data):
        rules = validated_data.pop('rules', [])
        with transaction.atomic():
            security_group = super(SecurityGroupSerializer, self).create(validated_data)
            for rule in rules:
                security_group.rules.add(rule)

        return security_group

    def update(self, instance, validated_data):
        rules = validated_data.pop('rules', [])
        new_rules = [rule for rule in rules if rule.id is None]
        existed_rules = set([rule for rule in rules if rule.id is not None])

        security_group = super(SecurityGroupSerializer, self).update(instance, validated_data)
        old_rules = set(security_group.rules.all())

        with transaction.atomic():
            removed_rules = old_rules - existed_rules
            for rule in removed_rules:
                rule.delete()

            for rule in new_rules:
                security_group.rules.add(rule)

        return security_group


class InstanceSecurityGroupSerializer(serializers.ModelSerializer):

    name = serializers.ReadOnlyField(source='security_group.name')
    rules = NestedSecurityGroupRuleSerializer(
        source='security_group.rules',
        many=True,
        read_only=True,
    )
    url = serializers.HyperlinkedRelatedField(
        source='security_group',
        lookup_field='uuid',
        view_name='openstack-sgp-detail',
        queryset=models.SecurityGroup.objects.all(),
    )
    description = serializers.ReadOnlyField(source='security_group.description')

    class Meta(object):
        model = models.InstanceSecurityGroup
        fields = ('url', 'name', 'rules', 'description')
        extra_kwargs = {
            'url': {'lookup_field': 'uuid'},
        }
        view_name = 'openstack-sgp-detail'


class InstanceSerializer(structure_serializers.VirtualMachineSerializer):

    service = serializers.HyperlinkedRelatedField(
        source='service_project_link.service',
        view_name='openstack-detail',
        read_only=True,
        lookup_field='uuid')

    service_project_link = serializers.HyperlinkedRelatedField(
        view_name='openstack-spl-detail',
        queryset=models.OpenStackServiceProjectLink.objects.all(),
        write_only=True)

    flavor = serializers.HyperlinkedRelatedField(
        view_name='openstack-flavor-detail',
        lookup_field='uuid',
        queryset=models.Flavor.objects.all().select_related('settings'),
        write_only=True)

    image = serializers.HyperlinkedRelatedField(
        view_name='openstack-image-detail',
        lookup_field='uuid',
        queryset=models.Image.objects.all().select_related('settings'),
        write_only=True)

    security_groups = InstanceSecurityGroupSerializer(
        many=True, required=False, read_only=False)

    skip_external_ip_assigment = serializers.BooleanField(write_only=True, default=False)

    class Meta(structure_serializers.VirtualMachineSerializer.Meta):
        model = models.Instance
        view_name = 'openstack-instance-detail'
        fields = structure_serializers.VirtualMachineSerializer.Meta.fields + (
            'flavor', 'image', 'system_volume_size', 'data_volume_size', 'skip_external_ip_assigment',
            'security_groups', 'internal_ips',
        )
        protected_fields = structure_serializers.VirtualMachineSerializer.Meta.protected_fields + (
            'flavor', 'image', 'system_volume_size', 'data_volume_size', 'skip_external_ip_assigment',
        )
        read_only_fields = structure_serializers.VirtualMachineSerializer.Meta.read_only_fields + (
            'internal_ips',
        )

    def get_fields(self):
        fields = super(InstanceSerializer, self).get_fields()
        fields['system_volume_size'].required = True
        return fields

    def validate(self, attrs):
        # skip validation on object update
        if self.instance is not None:
            return attrs

        settings = attrs['service_project_link'].service.settings
        service_project_link = attrs['service_project_link']
        flavor = attrs['flavor']
        image = attrs['image']

        if not service_project_link.floating_ips.filter(status='DOWN').exists():
            raise serializers.ValidationError(
                {'service_project_link': 'Links tenant does not have any free floating IP.'
                                         ' Try to allocate floating IP.'})

        if any([flavor.settings != settings, image.settings != settings]):
            raise serializers.ValidationError(
                "Flavor and image must belong to the same service settings as service project link.")

        if image.min_ram > flavor.ram:
            raise serializers.ValidationError(
                {'flavor': "RAM of flavor is not enough for selected image %s" % image.min_ram})

        if image.min_disk > attrs['system_volume_size']:
            raise serializers.ValidationError(
                {'system_volume_size': "System volume size has to be greater than %s" % image.min_disk})

        for security_group_data in attrs.get('security_groups', []):
            security_group = security_group_data['security_group']
            if security_group.service_project_link != attrs['service_project_link']:
                raise serializers.ValidationError(
                    "Security group {} has wrong service or project. New instance and its "
                    "security groups have to belong to same project and service".format(security_group.name))

        return attrs

    def create(self, validated_data):
        security_groups = [data['security_group'] for data in validated_data.pop('security_groups', [])]
        provision_data = {
            'flavor': validated_data.pop('flavor'),
            'image': validated_data.pop('image'),
            'ssh_key': validated_data.pop('ssh_key', None),
            'skip_external_ip_assigment': validated_data.pop('skip_external_ip_assigment', False)
        }

        instance = models.Instance(**validated_data)
        instance.provision(**provision_data)

        for sg in security_groups:
            instance.security_groups.create(security_group=sg)

        return instance

    def update(self, instance, validated_data):
        security_groups = validated_data.pop('security_groups', [])
        security_groups = [data['security_group'] for data in security_groups]
        instance = super(InstanceSerializer, self).update(instance, validated_data)

        instance.security_groups.all().delete()
        for sg in security_groups:
            instance.security_groups.create(security_group=sg)

        return instance


class InstanceImportSerializer(structure_serializers.BaseResourceImportSerializer):

    class Meta(structure_serializers.BaseResourceImportSerializer.Meta):
        model = models.Instance
        view_name = 'openstack-instance-detail'

    def create(self, validated_data):
        spl = validated_data['service_project_link']
        backend = spl.get_backend()

        try:
            backend_instance = backend.get_instance(validated_data['backend_id'])
        except OpenStackBackendError:
            raise serializers.ValidationError(
                {'backend_id': "Can't import instance with ID %s" % validated_data['backend_id']})

        backend_security_groups = backend_instance.nc_model_data.pop('security_groups')
        security_groups = spl.security_groups.filter(name__in=backend_security_groups)
        if security_groups.count() != len(backend_security_groups):
            raise serializers.ValidationError(
                {'backend_id': "Security groups for instance ID %s "
                               "are missed in NodeConductor" % validated_data['backend_id']})

        validated_data.update(backend_instance.nc_model_data)
        instance = super(InstanceImportSerializer, self).create(validated_data)

        for sg in security_groups:
            instance.security_groups.create(security_group=sg)

        return instance
