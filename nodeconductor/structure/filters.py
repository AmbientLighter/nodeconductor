from __future__ import unicode_literals

import django_filters
from django.contrib import auth
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from rest_framework.filters import BaseFilterBackend

from nodeconductor.core import filters as core_filters
from nodeconductor.core import models as core_models
from nodeconductor.logging.filters import ExternalAlertFilterBackend, BaseExternalFilter
from nodeconductor.structure import models
from nodeconductor.structure import serializers
from nodeconductor.structure import SupportedServices
from nodeconductor.structure.managers import filter_queryset_for_user


User = auth.get_user_model()


class GenericRoleFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return filter_queryset_for_user(queryset, request.user)


class CustomerFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        lookup_type='icontains',
    )
    native_name = django_filters.CharFilter(
        lookup_type='icontains',
    )
    abbreviation = django_filters.CharFilter(
        lookup_type='icontains',
    )
    contact_details = django_filters.CharFilter(
        lookup_type='icontains',
    )

    class Meta(object):
        model = models.Customer
        fields = [
            'name',
            'abbreviation',
            'contact_details',
            'native_name',
            'registration_code',
        ]
        order_by = [
            'name',
            'abbreviation',
            'contact_details',
            'native_name',
            'registration_code',
            # desc
            '-name',
            '-abbreviation',
            '-contact_details',
            '-native_name',
            '-registration_code',
        ]


class ProjectFilter(django_filters.FilterSet):
    customer = django_filters.CharFilter(
        name='customer__uuid',
        distinct=True,
    )

    customer_name = django_filters.CharFilter(
        name='customer__name',
        distinct=True,
        lookup_type='icontains'
    )

    customer_native_name = django_filters.CharFilter(
        name='customer__native_name',
        distinct=True,
        lookup_type='icontains'
    )

    customer_abbreviation = django_filters.CharFilter(
        name='customer__abbreviation',
        distinct=True,
        lookup_type='icontains'
    )

    project_group = django_filters.CharFilter(
        name='project_groups__uuid',
        distinct=True,
    )

    project_group_name = django_filters.CharFilter(
        name='project_groups__name',
        distinct=True,
        lookup_type='icontains'
    )

    name = django_filters.CharFilter(lookup_type='icontains')

    description = django_filters.CharFilter(lookup_type='icontains')

    class Meta(object):
        model = models.Project
        fields = [
            'project_group',
            'project_group_name',
            'name',
            'customer', 'customer_name', 'customer_native_name', 'customer_abbreviation',
            'description',
            'created',
        ]
        order_by = [
            'name',
            '-name',
            'created',
            '-created',
            'project_groups__name',
            '-project_groups__name',
            'customer__native_name',
            '-customer__native_name',
            'customer__name',
            '-customer__name',
            'customer__abbreviation',
            '-customer__abbreviation',
        ]

        order_by_mapping = {
            # Proper field naming
            'project_group_name': 'project_groups__name',
            'customer_name': 'customer__name',
            'customer_abbreviation': 'customer__abbreviation',
            'customer_native_name': 'customer__native_name',

            # Backwards compatibility
            'project_groups__name': 'project_groups__name',
        }


class ProjectGroupFilter(django_filters.FilterSet):
    customer = django_filters.CharFilter(
        name='customer__uuid',
        distinct=True,
    )
    customer_name = django_filters.CharFilter(
        name='customer__name',
        distinct=True,
        lookup_type='icontains',
    )
    customer_native_name = django_filters.CharFilter(
        name='customer__native_name',
        distinct=True,
        lookup_type='icontains',
    )

    customer_abbreviation = django_filters.CharFilter(
        name='customer__abbreviation',
        distinct=True,
        lookup_type='icontains',
    )

    name = django_filters.CharFilter(lookup_type='icontains')

    class Meta(object):
        model = models.ProjectGroup
        fields = [
            'name',
            'customer',
            'customer_name',
            'customer_native_name',
            'customer_abbreviation',
        ]
        order_by = [
            'name',
            '-name',
            'customer__name',
            '-customer__name',
            'customer__native_name',
            '-customer__native_name',
            'customer__abbreviation',
            '-customer__abbreviation',
        ]
        order_by_mapping = {
            'customer_name': 'customer__name',
            'customer_abbreviation': 'customer__abbreviation',
            'customer_native_name': 'customer__native_name',
        }


class ProjectGroupMembershipFilter(django_filters.FilterSet):
    project_group = django_filters.CharFilter(
        name='projectgroup__uuid',
    )

    project_group_name = django_filters.CharFilter(
        name='projectgroup__name',
        lookup_type='icontains',
    )

    project = django_filters.CharFilter(
        name='project__uuid',
    )

    project_name = django_filters.CharFilter(
        name='project__name',
        lookup_type='icontains',
    )

    class Meta(object):
        model = models.ProjectGroup.projects.through
        fields = [
            'project_group',
            'project_group_name',
            'project',
            'project_name',
        ]


class UserFilter(django_filters.FilterSet):
    project_group = django_filters.CharFilter(
        name='groups__projectrole__project__project_groups__name',
        distinct=True,
        lookup_type='icontains',
    )
    project = django_filters.CharFilter(
        name='groups__projectrole__project__name',
        distinct=True,
        lookup_type='icontains',
    )

    full_name = django_filters.CharFilter(lookup_type='icontains')
    username = django_filters.CharFilter()
    native_name = django_filters.CharFilter(lookup_type='icontains')
    job_title = django_filters.CharFilter(lookup_type='icontains')
    email = django_filters.CharFilter(lookup_type='icontains')
    is_active = django_filters.BooleanFilter()

    class Meta(object):
        model = User
        fields = [
            'full_name',
            'native_name',
            'organization',
            'organization_approved',
            'email',
            'phone_number',
            'description',
            'job_title',
            'project',
            'project_group',
            'username',
            'civil_number',
            'is_active',
        ]
        order_by = [
            'full_name',
            'native_name',
            'organization',
            'organization_approved',
            'email',
            'phone_number',
            'description',
            'job_title',
            'username',
            'is_active',
            # descending
            '-full_name',
            '-native_name',
            '-organization',
            '-organization_approved',
            '-email',
            '-phone_number',
            '-description',
            '-job_title',
            '-username',
            '-is_active',
        ]


# TODO: cover filtering/ordering with tests
class ProjectPermissionFilter(django_filters.FilterSet):
    project = django_filters.CharFilter(
        name='group__projectrole__project__uuid',
    )
    project_url = core_filters.URLFilter(
        view_name='project-detail',
        name='group__projectrole__project__uuid',
    )
    user_url = core_filters.URLFilter(
        view_name='user-detail',
        name='user__uuid',
    )
    username = django_filters.CharFilter(
        name='user__username',
        lookup_type='exact',
    )
    full_name = django_filters.CharFilter(
        name='user__full_name',
        lookup_type='icontains',
    )
    native_name = django_filters.CharFilter(
        name='user__native_name',
        lookup_type='icontains',
    )
    role = core_filters.MappedChoiceFilter(
        name='group__projectrole__role_type',
        choices=(
            ('admin', 'Administrator'),
            ('manager', 'Manager'),
            # TODO: Removing this drops support of filtering by numeric codes
            (models.ProjectRole.ADMINISTRATOR, 'Administrator'),
            (models.ProjectRole.MANAGER, 'Manager'),
        ),
        choice_mappings={
            'admin': models.ProjectRole.ADMINISTRATOR,
            'manager': models.ProjectRole.MANAGER,
        },
    )

    class Meta(object):
        model = User.groups.through
        fields = [
            'role',
            'project',
            'username',
            'full_name',
            'native_name',
        ]
        order_by = [
            'user__username',
            'user__full_name',
            'user__native_name',
            # desc
            '-user__username',
            '-user__full_name',
            '-user__native_name',
        ]


class ProjectGroupPermissionFilter(django_filters.FilterSet):
    project_group = django_filters.CharFilter(
        name='group__projectgrouprole__project_group__uuid',
    )
    project_group_url = core_filters.URLFilter(
        view_name='projectgroup-detail',
        name='group__projectgrouprole__project_group__uuid',
    )
    user_url = core_filters.URLFilter(
        view_name='user-detail',
        name='user__uuid',
    )
    username = django_filters.CharFilter(
        name='user__username',
        lookup_type='exact',
    )
    full_name = django_filters.CharFilter(
        name='user__full_name',
        lookup_type='icontains',
    )
    native_name = django_filters.CharFilter(
        name='user__native_name',
        lookup_type='icontains',
    )
    role = core_filters.MappedChoiceFilter(
        name='group__projectgrouprole__role_type',
        choices=(
            ('manager', 'Manager'),
            # TODO: Removing this drops support of filtering by numeric codes
            (models.ProjectGroupRole.MANAGER, 'Manager'),
        ),
        choice_mappings={
            'manager': models.ProjectGroupRole.MANAGER,
        },
    )

    class Meta(object):
        model = User.groups.through
        fields = [
            'role',
            'project_group',
            'username',
            'full_name',
            'native_name',
        ]
        order_by = [
            'user__username',
            'user__full_name',
            'user__native_name',
            # desc
            '-user__username',
            '-user__full_name',
            '-user__native_name',

        ]


class CustomerPermissionFilter(django_filters.FilterSet):
    customer = django_filters.CharFilter(
        name='group__customerrole__customer__uuid',
    )
    customer_url = core_filters.URLFilter(
        view_name='customer-detail',
        name='group__customerrole__customer__uuid',
    )
    user_url = core_filters.URLFilter(
        view_name='user-detail',
        name='user__uuid',
    )
    username = django_filters.CharFilter(
        name='user__username',
        lookup_type='exact',
    )
    full_name = django_filters.CharFilter(
        name='user__full_name',
        lookup_type='icontains',
    )
    native_name = django_filters.CharFilter(
        name='user__native_name',
        lookup_type='icontains',
    )
    role = core_filters.MappedChoiceFilter(
        name='group__customerrole__role_type',
        choices=(
            ('owner', 'Owner'),
            # TODO: Removing this drops support of filtering by numeric codes
            (models.CustomerRole.OWNER, 'Owner'),
        ),
        choice_mappings={
            'owner': models.CustomerRole.OWNER,
        },
    )

    class Meta(object):
        model = User.groups.through
        fields = [
            'role',
            'customer',
            'username',
            'full_name',
            'native_name',
        ]
        order_by = [
            'user__username',
            'user__full_name',
            'user__native_name',
            # desc
            '-user__username',
            '-user__full_name',
            '-user__native_name',

        ]


class SshKeyFilter(django_filters.FilterSet):
    uuid = django_filters.CharFilter()
    user_uuid = django_filters.CharFilter(
        name='user__uuid'
    )
    name = django_filters.CharFilter(lookup_type='icontains')

    class Meta(object):
        model = core_models.SshPublicKey
        fields = [
            'name',
            'fingerprint',
            'uuid',
            'user_uuid'
        ]
        order_by = [
            'name',
            '-name',
        ]


class ServiceSettingsFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_type='icontains')
    type = core_filters.MappedChoiceFilter(
        choices=SupportedServices.Types.get_direct_filter_mapping(),
        choice_mappings=SupportedServices.Types.get_reverse_filter_mapping(),
    )
    state = core_filters.MappedChoiceFilter(
        choices=(
            ('sync_scheduled', 'Sync Scheduled'),
            ('syncing', 'Syncing'),
            ('in_sync', 'In Sync'),
            ('erred', 'Erred'),
        ),
        choice_mappings={
            'sync_scheduled': core_models.SynchronizationStates.SYNCING_SCHEDULED,
            'syncing': core_models.SynchronizationStates.SYNCING,
            'in_sync': core_models.SynchronizationStates.IN_SYNC,
            'erred': core_models.SynchronizationStates.ERRED,
        },
    )

    class Meta(object):
        model = models.ServiceSettings
        fields = ('name', 'type', 'state')


class BaseServiceFilter(django_filters.FilterSet):
    customer_uuid = django_filters.CharFilter(name='customer__uuid')
    customer = core_filters.URLFilter(view_name='customer-detail', name='customer__uuid')
    name = django_filters.CharFilter(lookup_type='icontains')
    project_uuid = django_filters.CharFilter(name='projects__uuid', distinct=True)

    class Meta(object):
        model = models.Service


class BaseServiceProjectLinkFilter(django_filters.FilterSet):
    service_uuid = django_filters.CharFilter(name='service__uuid')
    project_uuid = django_filters.CharFilter(name='project__uuid')
    project = core_filters.URLFilter(view_name='project-detail', name='project__uuid')

    class Meta(object):
        model = models.ServiceProjectLink


class BaseResourceFilter(django_filters.FilterSet):
    project_uuid = django_filters.CharFilter(name='service_project_link__project__uuid')
    customer_uuid = django_filters.CharFilter(name='service_project_link__service__customer__uuid')
    service_uuid = django_filters.CharFilter(name='service_project_link__service__uuid')
    name = django_filters.CharFilter(lookup_type='icontains')

    class Meta(object):
        model = models.Resource
        fields = ('project_uuid', 'customer_uuid', 'service_uuid', 'name')


class BaseServicePropertyFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        name='name',
        lookup_type='icontains',
    )

    class Meta(object):
        model = models.ServiceProperty
        fields = ('name',)


class ServicePropertySettingsFilter(BaseServicePropertyFilter):
    settings_uuid = django_filters.CharFilter(name='settings__uuid')

    class Meta(BaseServicePropertyFilter.Meta):
        fields = BaseServicePropertyFilter.Meta.fields + ('settings_uuid', )


class AggregateFilter(BaseExternalFilter):
    """
    Filter by aggregate
    """

    def filter(self, request, queryset, view):
        # Don't apply filter if aggregate is not specified
        if 'aggregate' not in request.query_params:
            return queryset

        serializer = serializers.AggregateSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        aggregates = serializer.get_aggregates(request.user)
        projects = serializer.get_projects(request.user)
        querysets = [aggregates, projects]
        aggregates_ids = list(aggregates.values_list('id', flat=True))
        query = {serializer.data['aggregate'] + '__in': aggregates_ids}

        all_models = models.Resource.get_all_models() + \
                     models.Service.get_all_models() + \
                     models.ServiceProjectLink.get_all_models()
        for model in all_models:
            qs = model.objects.filter(**query).all()
            querysets.append(filter_queryset_for_user(qs, request.user))

        aggregate_query = Q()
        for qs in querysets:
            content_type = ContentType.objects.get_for_model(qs.model)
            ids = qs.values_list('id', flat=True)
            aggregate_query |= Q(content_type=content_type, object_id__in=ids)

        return queryset.filter(aggregate_query)

ExternalAlertFilterBackend.register(AggregateFilter())
