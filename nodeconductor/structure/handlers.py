from __future__ import unicode_literals

import logging

from django.db import models, transaction
from django.contrib.auth.models import Group

from nodeconductor.core.tasks import send_task
from nodeconductor.core.models import SshPublicKey
from nodeconductor.quotas import handlers as quotas_handlers
from nodeconductor.structure import signals
from nodeconductor.structure.log import event_logger
from nodeconductor.structure.filters import filter_queryset_for_user
from nodeconductor.structure.models import (CustomerRole, Project, ProjectRole, ProjectGroupRole,
                                            Customer, ProjectGroup, ServiceProjectLink)


logger = logging.getLogger(__name__)


def sync_ssh_public_keys(action, public_key=None, project=None, user=None):
    """ Call supplied background task to push or remove SSH key(s) for a service.
        Use supplied public_key or lookup it by project & user.
    """

    service_project_links = []
    if public_key:
        ssh_public_key_uuids = [public_key.uuid.hex]
        for spl_cls in ServiceProjectLink.get_all_models():
            for spl in filter_queryset_for_user(spl_cls.objects.all(), public_key.user):
                service_project_links.append(spl.to_string())

        # Key has been already removed from DB and can't be
        # recovered in celery task so call backend here
        if action == 'REMOVE':
            for spl in service_project_links:
                backend = spl.get_backend()
                backend.remove_ssh_key(public_key, spl)
            return

    elif project and user:
        ssh_public_key_uuids = list(SshPublicKey.objects.filter(
            user=user).values_list('uuid', flat=True))
        for spl_cls in ServiceProjectLink.get_all_models():
            for spl in spl_cls.objects.filter(project=project):
                service_project_links.append(spl.to_string())

    if ssh_public_key_uuids and service_project_links:
        send_task('structure', 'sync_ssh_public_keys')(
            action, ssh_public_key_uuids, service_project_links)


def propagate_users_key_to_his_projects_services(sender, instance=None, created=False, **kwargs):
    """ Propagate ssh public keys of users involved in the project """
    if created:
        ssh_public_key_uuids = SshPublicKey.objects.filter(
            user__groups__projectrole__project=instance.project).values_list('uuid', flat=True)
        send_task('structure', 'sync_ssh_public_keys')(
            'PUSH', list(ssh_public_key_uuids), [instance.to_string()])


def propagate_new_users_key_to_his_projects_services(sender, instance=None, created=False, **kwargs):
    """ Propagate new ssh public key to all services it belongs via user projects """
    if created:
        sync_ssh_public_keys('PUSH', public_key=instance)


def remove_stale_users_key_from_his_projects_services(sender, instance=None, **kwargs):
    """ Remove new ssh public key from all services it belongs via user projects """
    sync_ssh_public_keys('REMOVE', public_key=instance)


def propagate_users_keys_to_services_of_newly_granted_project(sender, structure, user, role, **kwargs):
    """ Propagate user's ssh public key to a service of new project """
    sync_ssh_public_keys('PUSH', project=structure, user=user)


def remove_stale_users_keys_from_services_of_revoked_project(sender, structure, user, role, **kwargs):
    """ Remove user's ssh public key from a service of old project """
    sync_ssh_public_keys('REMOVE', project=structure, user=user)


def prevent_non_empty_project_group_deletion(sender, instance, **kwargs):
    related_projects = Project.objects.filter(project_groups=instance)

    if related_projects.exists():
        raise models.ProtectedError(
            "Cannot delete some instances of model 'ProjectGroup' because "
            "they have connected 'Projects'",
            related_projects
        )


def create_project_roles(sender, instance, created, **kwargs):
    if not created:
        return

    with transaction.atomic():
        admin_group = Group.objects.create(name='Role: {0} admin'.format(instance.uuid))
        mgr_group = Group.objects.create(name='Role: {0} mgr'.format(instance.uuid))

        instance.roles.create(role_type=ProjectRole.ADMINISTRATOR, permission_group=admin_group)
        instance.roles.create(role_type=ProjectRole.MANAGER, permission_group=mgr_group)


def create_customer_roles(sender, instance, created, **kwargs):
    if not created:
        return

    with transaction.atomic():
        owner_group = Group.objects.create(name='Role: {0} owner'.format(instance.uuid))

        instance.roles.create(role_type=CustomerRole.OWNER, permission_group=owner_group)


def create_project_group_roles(sender, instance, created, **kwargs):
    if not created:
        return

    with transaction.atomic():
        mgr_group = Group.objects.create(name='Role: {0} group mgr'.format(instance.uuid))
        instance.roles.create(role_type=ProjectGroupRole.MANAGER, permission_group=mgr_group)


def log_customer_save(sender, instance, created=False, **kwargs):
    if created:
        event_logger.customer.info(
            'Customer {customer_name} has been created.',
            event_type='customer_creation_succeeded',
            event_context={
                'customer': instance,
            })
    else:
        event_logger.customer.info(
            'Customer {customer_name} has been updated.',
            event_type='customer_update_succeeded',
            event_context={
                'customer': instance,
            })


def log_customer_delete(sender, instance, **kwargs):
    event_logger.customer.info(
        'Customer {customer_name} has been deleted.',
        event_type='customer_deletion_succeeded',
        event_context={
            'customer': instance,
        })


def log_project_group_save(sender, instance, created=False, **kwargs):
    if created:
        event_logger.project_group.info(
            'Project group {project_group_name} has been created.',
            event_type='project_group_creation_succeeded',
            event_context={
                'project_group': instance,
            })
    else:
        event_logger.project_group.info(
            'Project group {project_group_name} has been updated.',
            event_type='project_group_update_succeeded',
            event_context={
                'project_group': instance,
            })


def log_project_group_delete(sender, instance, **kwargs):
    event_logger.project_group.info(
        'Project group {project_group_name} has been deleted.',
        event_type='project_group_deletion_succeeded',
        event_context={
            'project_group': instance,
        })


def log_project_save(sender, instance, created=False, **kwargs):
    if created:
        event_logger.project.info(
            'Project {project_name} has been created.',
            event_type='project_creation_succeeded',
            event_context={
                'project': instance,
                'project_group': instance.project_groups.first(),
            })
    else:
        event_logger.project.info(
            'Project {project_name} has been updated.',
            event_type='project_update_succeeded',
            event_context={
                'project': instance,
                'project_group': instance.project_groups.first(),
            })


def log_project_delete(sender, instance, **kwargs):
    event_logger.project.info(
        'Project {project_name} has been deleted.',
        event_type='project_deletion_succeeded',
        event_context={
            'project': instance,
            'project_group': instance.project_groups.first(),
        })


def log_customer_role_granted(sender, structure, user, role, **kwargs):
    event_logger.customer_role.info(
        'User {affected_user_username} has gained role of {role_name} in customer {customer_name}.',
        event_type='role_granted',
        event_context={
            'customer': structure,
            'affected_user': user,
            'structure_type': 'customer',
            'role_name': structure.roles.get(role_type=role).get_role_type_display().lower(),
        })


def log_customer_role_revoked(sender, structure, user, role, **kwargs):
    event_logger.customer_role.info(
        'User {affected_user_username} has lost role of {role_name} in customer {customer_name}.',
        event_type='role_revoked',
        event_context={
            'customer': structure,
            'affected_user': user,
            'structure_type': 'customer',
            'role_name': structure.roles.get(role_type=role).get_role_type_display().lower(),
        })


def log_project_role_granted(sender, structure, user, role, **kwargs):
    event_logger.project_role.info(
        'User {affected_user_username} has gained role of {role_name} in project {project_name}.',
        event_type='role_granted',
        event_context={
            'project': structure,
            'project_group': structure.project_groups.first(),
            'affected_user': user,
            'structure_type': 'project',
            'role_name': structure.roles.get(role_type=role).get_role_type_display().lower(),
        })


def log_project_role_revoked(sender, structure, user, role, **kwargs):
    event_logger.project_role.info(
        'User {affected_user_username} has revoked role of {role_name} in project {project_name}.',
        event_type='role_revoked',
        event_context={
            'project': structure,
            'project_group': structure.project_groups.first(),
            'affected_user': user,
            'structure_type': 'project',
            'role_name': structure.roles.get(role_type=role).get_role_type_display().lower(),
        })


def log_project_group_role_granted(sender, structure, user, role, **kwargs):
    event_logger.project_group_role.info(
        'User {affected_user_username} has gained role of {role_name}'
        ' in project group {project_group_name}.',
        event_type='role_granted',
        event_context={
            'project_group': structure,
            'affected_user': user,
            'structure_type': 'project_group',
            'role_name': structure.roles.get(role_type=role).get_role_type_display().lower(),
        })


def log_project_group_role_revoked(sender, structure, user, role, **kwargs):
    event_logger.project_group_role.info(
        'User {affected_user_username} has gained role of {role_name}'
        ' in project group {project_group_name}.',
        event_type='role_revoked',
        event_context={
            'project_group': structure,
            'affected_user': user,
            'structure_type': 'project_group',
            'role_name': structure.roles.get(role_type=role).get_role_type_display().lower(),
        })


change_customer_nc_projects_quota = quotas_handlers.quantity_quota_handler_factory(
    path_to_quota_scope='customer',
    quota_name='nc_project_count',
)


def change_customer_nc_users_quota(sender, structure, user, role, signal, **kwargs):
    """ Modify nc_user_count quota usage on structure role grant or revoke """
    assert signal in (signals.structure_role_granted, signals.structure_role_revoked), \
        'Handler "change_customer_nc_users_quota" has to be used only with structure_role signals'
    assert sender in (Customer, Project, ProjectGroup), \
        'Handler "change_customer_nc_users_quota" works only with Project, Customer and ProjectGroup models'

    if sender == Customer:
        customer = structure
        customer_users = customer.get_users().exclude(groups__customerrole__role_type=role)
    elif sender == Project:
        customer = structure.customer
        customer_users = customer.get_users().exclude(groups__projectrole__role_type=role)
    elif sender == ProjectGroup:
        customer = structure.customer
        customer_users = customer.get_users().exclude(groups__projectgrouprole__role_type=role)

    if user not in customer_users:
        if signal == signals.structure_role_granted:
            customer.add_quota_usage('nc_user_count', 1)
        else:
            customer.add_quota_usage('nc_user_count', -1)
