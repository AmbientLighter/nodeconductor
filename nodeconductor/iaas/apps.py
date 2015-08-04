from __future__ import unicode_literals

from django.apps import AppConfig
from django.db.models import signals
from django_fsm.signals import post_transition

from nodeconductor.core import handlers as core_handlers
from nodeconductor.core.signals import pre_serializer_fields


class IaasConfig(AppConfig):
    name = 'nodeconductor.iaas'
    verbose_name = "NodeConductor IaaS"

    # See, https://docs.djangoproject.com/en/1.7/ref/applications/#django.apps.AppConfig.ready
    def ready(self):
        Instance = self.get_model('Instance')
        CloudProjectMembership = self.get_model('CloudProjectMembership')

        from nodeconductor.iaas import handlers
        from nodeconductor.structure.serializers import CustomerSerializer, ProjectSerializer

        pre_serializer_fields.connect(
            handlers.add_clouds_to_related_model,
            sender=CustomerSerializer,
            dispatch_uid='nodeconductor.iaas.handlers.add_clouds_to_customer',
        )

        pre_serializer_fields.connect(
            handlers.add_clouds_to_related_model,
            sender=ProjectSerializer,
            dispatch_uid='nodeconductor.iaas.handlers.add_clouds_to_project',
        )

        signals.post_save.connect(
            handlers.create_initial_security_groups,
            sender=CloudProjectMembership,
            dispatch_uid='nodeconductor.iaas.handlers.create_initial_security_groups',
        )

        # protect against a deletion of the Instance with connected backups
        # TODO: introduces dependency of IaaS on Backups, should be reconsidered
        signals.pre_delete.connect(
            handlers.prevent_deletion_of_instances_with_connected_backups,
            sender=Instance,
            dispatch_uid='nodeconductor.iaas.handlers.prevent_deletion_of_instances_with_connected_backups',
        )

        signals.pre_save.connect(
            core_handlers.preserve_fields_before_update,
            sender=Instance,
            dispatch_uid='nodeconductor.iaas.handlers.preserve_fields_before_update',
        )

        # if instance name is updated, zabbix host visible name should be also updated
        signals.post_save.connect(
            handlers.check_instance_name_update,
            sender=Instance,
            dispatch_uid='nodeconductor.iaas.handlers.check_instance_name_update',
        )

        signals.pre_save.connect(
            handlers.set_cpm_default_availability_zone,
            sender=CloudProjectMembership,
            dispatch_uid='nodeconductor.iaas.handlers.set_cpm_default_availability_zone',
        )

        signals.post_save.connect(
            handlers.increase_quotas_usage_on_instance_creation,
            sender=Instance,
            dispatch_uid='nodeconductor.iaas.handlers.increase_quotas_usage_on_instance_creation',
        )

        signals.post_delete.connect(
            handlers.decrease_quotas_usage_on_instances_deletion,
            sender=Instance,
            dispatch_uid='nodeconductor.iaas.handlers.decrease_quotas_usage_on_instances_deletion',
        )

        signals.post_delete.connect(
            handlers.delete_order,
            sender=Instance,
            dispatch_uid='nodeconductor.iaas.handlers.delete_order',
        )

        post_transition.connect(
            handlers.track_order,
            sender=Instance,
            dispatch_uid='nodeconductor.iaas.handlers.track_order',
        )
