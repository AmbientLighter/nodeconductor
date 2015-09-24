EVENT_FEATURES = {
    'users': [
        'auth_logged_in_with_username',
        'user_activated',
        'user_deactivated',
        'user_creation_succeeded',
        'user_deletion_succeeded',
        'user_update_succeeded',
        'role_granted',
        'role_revoked',
    ],
    'password': [
        'user_password_updated',
    ],
    'ssh': [
        'ssh_key_creation_succeeded',
        'ssh_key_deletion_succeeded',
        'ssh_key_push_succeeded',
        'ssh_key_push_failed',
        'ssh_key_remove_succeeded',
        'ssh_key_remove_failed',
    ],
    'projects': [
        'project_creation_succeeded',
        'project_deletion_succeeded',
        'project_update_succeeded',
        'quota_threshold_reached'
    ],
    'project_groups': [
        'project_added_to_project_group',
        'project_group_creation_succeeded',
        'project_group_deletion_succeeded',
        'project_group_update_succeeded',
        'project_removed_from_project_group',
    ],
    'customers': [
        'customer_creation_succeeded',
        'customer_deletion_succeeded',
        'customer_update_succeeded',
        'customer_account_credited',
        'customer_account_debited',
        'user_organization_approved',
        'user_organization_claimed',
        'user_organization_rejected',
        'user_organization_removed',
    ],
    'payments': [
        'payment_approval_succeeded',
        'payment_cancel_succeeded',
        'payment_creation_succeeded',
    ],
    'invoices': [
        'invoice_creation_succeeded',
        'invoice_deletion_succeeded',
        'invoice_update_succeeded',
    ],
    'vms': [
        'resource_created',
        'resource_deleted',
        'resource_imported',
    ],
    'openStackPrivateCloud': [
        'iaas_instance_application_became_available',
        'iaas_instance_application_deployment_succeeded',
        'iaas_instance_application_failed',
        'iaas_instance_creation_failed',
        'iaas_instance_creation_scheduled',
        'iaas_instance_creation_succeeded',
        'iaas_instance_deletion_failed',
        'iaas_instance_deletion_succeeded',
        'iaas_instance_flavor_change_failed',
        'iaas_instance_flavor_change_scheduled',
        'iaas_instance_flavor_change_succeeded',
        'iaas_instance_import_failed',
        'iaas_instance_import_scheduled',
        'iaas_instance_import_succeeded',
        'iaas_instance_licenses_added',
        'iaas_instance_restart_failed',
        'iaas_instance_restart_succeeded',
        'iaas_instance_start_failed',
        'iaas_instance_start_succeeded',
        'iaas_instance_stop_failed',
        'iaas_instance_stop_succeeded',
        'iaas_instance_update_succeeded',
        'iaas_instance_volume_extension_scheduled',
        'iaas_membership_sync_failed',
        'iaas_service_sync_failed',
    ],
    'backups': [
        'iaas_backup_creation_failed',
        'iaas_backup_creation_scheduled',
        'iaas_backup_creation_succeeded',
        'iaas_backup_deletion_failed',
        'iaas_backup_deletion_scheduled',
        'iaas_backup_deletion_succeeded',
        'iaas_backup_restoration_failed',
        'iaas_backup_restoration_scheduled',
        'iaas_backup_restoration_succeeded',
        'iaas_backup_schedule_activated',
        'iaas_backup_schedule_creation_succeeded',
        'iaas_backup_schedule_deactivated',
        'iaas_backup_schedule_deletion_succeeded',
        'iaas_backup_schedule_update_succeeded',
    ],
    'templates': [
        'template_creation_succeeded',
        'template_deletion_succeeded',
        'template_service_creation_succeeded',
        'template_service_deletion_succeeded',
        'template_service_update_succeeded',
        'template_update_succeeded',
    ],
    'monitoring': [
        'zabbix_host_creation_failed',
        'zabbix_host_creation_succeeded',
        'zabbix_host_deletion_failed',
        'zabbix_host_deletion_succeeded',
    ],
}

ALERT_FEATURES = {
    'services': [
        'customer_has_zero_services',
        'service_unavailable',
        'customer_service_count_exceeded',
        'service_has_unmanaged_resources'
    ],
    'resources': [
        'customer_has_zero_resources',
        'service_has_unmanaged_resources',
        'resource_disappeared_from_backend',
        'customer_resource_count_exceeded'
    ],
    'projects': [
        'customer_has_zero_projects',
        'customer_project_count_exceeded'
    ],
    'quota': [
        'customer_projected_costs_exceeded',
        'quota_usage_is_over_threshold'
    ]
}


def features_to_types(mapping, features):
    event_types = set()
    for feature in features:
        event_types.update(mapping.get(feature, []))
    return list(event_types)


def features_to_events(features):
    return features_to_types(EVENT_FEATURES, features)


def features_to_alerts(features):
    return features_to_types(ALERT_FEATURES, features)
