from __future__ import unicode_literals

from django.apps import AppConfig
from django.contrib.auth import get_user_model
from django.db import models as django_models
from django.db.models import signals

from nodeconductor.core.models import SshPublicKey
from nodeconductor.quotas import handlers as quotas_handlers
from nodeconductor.structure.models import ServiceProjectLink
from nodeconductor.structure import filters
from nodeconductor.structure import handlers
from nodeconductor.structure import signals as structure_signals
from nodeconductor.structure import SupportedServices


class StructureConfig(AppConfig):
    name = 'nodeconductor.structure'
    verbose_name = "NodeConductor Structure"

    # See, https://docs.djangoproject.com/en/1.7/ref/applications/#django.apps.AppConfig.ready
    def ready(self):
        User = get_user_model()
        Customer = self.get_model('Customer')
        Project = self.get_model('Project')
        ProjectGroup = self.get_model('ProjectGroup')

        signals.post_save.connect(
            handlers.log_customer_save,
            sender=Customer,
            dispatch_uid='nodeconductor.structure.handlers.log_customer_save',
        )

        signals.post_delete.connect(
            handlers.log_customer_delete,
            sender=Customer,
            dispatch_uid='nodeconductor.structure.handlers.log_customer_delete',
        )

        signals.post_save.connect(
            handlers.create_customer_roles,
            sender=Customer,
            dispatch_uid='nodeconductor.structure.handlers.create_customer_roles',
        )

        signals.post_save.connect(
            handlers.create_project_roles,
            sender=Project,
            dispatch_uid='nodeconductor.structure.handlers.create_project_roles',
        )

        signals.post_save.connect(
            handlers.log_project_save,
            sender=Project,
            dispatch_uid='nodeconductor.structure.handlers.log_project_save',
        )

        signals.post_delete.connect(
            handlers.log_project_delete,
            sender=Project,
            dispatch_uid='nodeconductor.structure.handlers.log_project_delete',
        )

        signals.post_save.connect(
            handlers.create_project_group_roles,
            sender=ProjectGroup,
            dispatch_uid='nodeconductor.structure.handlers.create_project_group_roles',
        )

        signals.pre_delete.connect(
            handlers.prevent_non_empty_project_group_deletion,
            sender=ProjectGroup,
            dispatch_uid='nodeconductor.structure.handlers.prevent_non_empty_project_group_deletion',
        )

        signals.post_save.connect(
            handlers.log_project_group_save,
            sender=ProjectGroup,
            dispatch_uid='nodeconductor.structure.handlers.log_project_group_save',
        )

        signals.post_delete.connect(
            handlers.log_project_group_delete,
            sender=ProjectGroup,
            dispatch_uid='nodeconductor.structure.handlers.log_project_group_delete',
        )

        filters.set_permissions_for_model(
            User.groups.through,
            customer_path='group__projectrole__project__customer',
            project_group_path='group__projectrole__project__project_groups',
            project_path='group__projectrole__project',
        )

        # quotas creation
        signals.post_save.connect(
            quotas_handlers.add_quotas_to_scope,
            sender=Project,
            dispatch_uid='nodeconductor.structure.handlers.add_quotas_to_project',
        )

        signals.post_save.connect(
            quotas_handlers.add_quotas_to_scope,
            sender=Customer,
            dispatch_uid='nodeconductor.structure.handlers.add_quotas_to_customer',
        )

        # increase nc_project_count quota usage on project creation
        signals.post_save.connect(
            handlers.change_customer_nc_projects_quota,
            sender=Project,
            dispatch_uid='nodeconductor.structure.handlers.increase_customer_nc_projects_quota',
        )

        # decrease nc_project_count quota usage on project deletion
        signals.post_delete.connect(
            handlers.change_customer_nc_projects_quota,
            sender=Project,
            dispatch_uid='nodeconductor.structure.handlers.decrease_customer_nc_projects_quota',
        )

        # increase nc_user_count quota usage on adding user to customer
        structure_models_with_roles = (Customer, Project, ProjectGroup)
        for model in structure_models_with_roles:
            name = 'increase_customer_nc_users_quota_on_adding_user_to_%s' % model.__name__
            structure_signals.structure_role_granted.connect(
                handlers.change_customer_nc_users_quota,
                sender=model,
                dispatch_uid='nodeconductor.structure.handlers.%s' % name,
            )

        # decrease nc_user_count quota usage on removing user from customer
        for model in structure_models_with_roles:
            name = 'decrease_customer_nc_users_quota_on_adding_user_to_%s' % model.__name__
            structure_signals.structure_role_revoked.connect(
                handlers.change_customer_nc_users_quota,
                sender=model,
                dispatch_uid='nodeconductor.structure.handlers.%s' % name,
            )

        structure_signals.structure_role_granted.connect(
            handlers.log_customer_role_granted,
            sender=Customer,
            dispatch_uid='nodeconductor.structure.handlers.log_customer_role_granted',
        )

        structure_signals.structure_role_revoked.connect(
            handlers.log_customer_role_revoked,
            sender=Customer,
            dispatch_uid='nodeconductor.structure.handlers.log_customer_role_revoked',
        )

        structure_signals.structure_role_granted.connect(
            handlers.log_project_role_granted,
            sender=Project,
            dispatch_uid='nodeconductor.structure.handlers.log_project_role_granted',
        )

        structure_signals.structure_role_revoked.connect(
            handlers.log_project_role_revoked,
            sender=Project,
            dispatch_uid='nodeconductor.structure.handlers.log_project_role_revoked',
        )

        structure_signals.structure_role_granted.connect(
            handlers.log_project_group_role_granted,
            sender=ProjectGroup,
            dispatch_uid='nodeconductor.structure.handlers.log_project_group_role_granted',
        )

        structure_signals.structure_role_revoked.connect(
            handlers.log_project_group_role_revoked,
            sender=ProjectGroup,
            dispatch_uid='nodeconductor.structure.handlers.log_project_group_role_revoked',
        )

        for model in ServiceProjectLink.get_all_models():
            name = 'propagate_ssh_keys_for_%s' % model.__name__
            signals.post_save.connect(
                handlers.propagate_user_to_his_projects_services,
                sender=model,
                dispatch_uid='nodeconductor.structure.handlers.%s' % name,
            )

        signals.pre_delete.connect(
            handlers.remove_stale_user_from_his_projects_services,
            sender=User,
            dispatch_uid='nodeconductor.structure.handlers.remove_stale_user_from_his_projects_services',
        )

        signals.post_save.connect(
            handlers.propagate_new_users_key_to_his_projects_services,
            sender=SshPublicKey,
            dispatch_uid='nodeconductor.structure.handlers.propagate_new_users_key_to_his_projects_services',
        )

        signals.post_delete.connect(
            handlers.remove_stale_users_key_from_his_projects_services,
            sender=SshPublicKey,
            dispatch_uid='nodeconductor.structure.handlers.remove_stale_users_key_from_his_projects_services',
        )

        structure_signals.structure_role_granted.connect(
            handlers.propagate_user_to_services_of_newly_granted_project,
            sender=Project,
            dispatch_uid='nodeconductor.structure.handlers.propagate_user_to_services_of_newly_granted_project',
        )

        structure_signals.structure_role_revoked.connect(
            handlers.remove_stale_user_from_services_of_revoked_project,
            sender=Project,
            dispatch_uid='nodeconductor.structure.handlers.remove_stale_user_from_services_of_revoked_project',
        )

        structure_signals.customer_account_credited.connect(
            handlers.log_customer_account_credited,
            sender=Customer,
            dispatch_uid='nodeconductor.structure.handlers.log_customer_account_credited',
        )

        structure_signals.customer_account_debited.connect(
            handlers.log_customer_account_debited,
            sender=Customer,
            dispatch_uid='nodeconductor.structure.handlers.log_customer_account_debited',
        )

        resource_models = SupportedServices.get_resource_models().values()
        for model in resource_models:
            signals.post_save.connect(
                handlers.change_project_nc_resource_quota,
                sender=model,
                dispatch_uid='nodeconductor.structure.handlers.increase_project_nc_resource_quota_%s' % model.__name__,
            )

            signals.post_delete.connect(
                handlers.change_project_nc_resource_quota,
                sender=model,
                dispatch_uid='nodeconductor.structure.handlers.decrease_project_nc_resource_quota_%s' % model.__name__,
            )

        links_models = [m for m in django_models.get_models() if issubclass(m, ServiceProjectLink)]
        for model in links_models:
            signals.post_save.connect(
                handlers.change_project_nc_service_quota,
                sender=model,
                dispatch_uid='nodeconductor.structure.handlers.increase_project_nc_service_quota_%s' % model.__name__,
            )

            signals.post_delete.connect(
                handlers.change_project_nc_service_quota,
                sender=model,
                dispatch_uid='nodeconductor.structure.handlers.decrease_project_nc_service_quota_%s' % model.__name__,
            )
