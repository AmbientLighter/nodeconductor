from __future__ import unicode_literals

from rest_framework import serializers

from nodeconductor.core.serializers import GenericRelatedField, AugmentedSerializerMixin
from nodeconductor.cost_tracking import models
from nodeconductor.structure import models as structure_models


class PriceEstimateSerializer(AugmentedSerializerMixin, serializers.HyperlinkedModelSerializer):
    scope = GenericRelatedField(related_models=models.PriceEstimate.get_editable_estimated_models())
    scope_name = serializers.SerializerMethodField()
    scope_type = serializers.SerializerMethodField()

    class Meta(object):
        model = models.PriceEstimate
        fields = ('url', 'uuid', 'scope', 'total', 'details', 'month', 'year',
                  'is_manually_input', 'scope_name', 'scope_type')
        read_only_fields = ('is_manually_input',)
        extra_kwargs = {
            'url': {'lookup_field': 'uuid'},
        }
        protected_fields = ('scope', 'year', 'month')

    def validate(self, data):
        if self.instance is None and models.PriceEstimate.objects.filter(
                scope=data['scope'], year=data['year'], month=data['month'], is_manually_input=True).exists():
            raise serializers.ValidationError(
                'Estimate for given month already exists. Use PATCH request to update it.')
        return data

    def create(self, validated_data):
        validated_data['is_manually_input'] = True
        price_estimate = super(PriceEstimateSerializer, self).create(validated_data)
        return price_estimate

    def get_scope_name(self, obj):
        return str(obj.scope)

    def get_scope_type(self, obj):
        models = (structure_models.Resource,
                  structure_models.Service,
                  structure_models.ServiceProjectLink,
                  structure_models.Project,
                  structure_models.Customer)
        for model in models:
            if isinstance(obj.scope, model):
                return model._meta.model_name


class YearMonthField(serializers.CharField):
    """ Field that support year-month representation in format YYYY.MM """

    def to_internal_value(self, value):
        try:
            year, month = [int(el) for el in value.split('.')]
        except ValueError:
            raise serializers.ValidationError('Value "{}" should be valid be in format YYYY.MM'.format(value))
        if not 0 < month < 13:
            raise serializers.ValidationError('Month has to be from 1 to 12')
        return year, month


class PriceEstimateDateFilterSerializer(serializers.Serializer):
    date_list = serializers.ListField(
        child=YearMonthField(),
        required=False
    )


class PriceEstimateDateRangeFilterSerializer(serializers.Serializer):
    start = YearMonthField(required=False)
    end = YearMonthField(required=False)

    def validate(self, data):
        if 'start' in data and 'end' in data and data['start'] >= data['end']:
            raise serializers.ValidationError('Start has to be earlier than end.')
        return data


class PriceListItemSerializer(AugmentedSerializerMixin, serializers.HyperlinkedModelSerializer):
    service = GenericRelatedField(related_models=structure_models.Service.get_all_models())

    class Meta:
        model = models.PriceListItem
        lookup_field = 'uuid'
        fields = ('url', 'uuid', 'key', 'item_type', 'value', 'units', 'service')
        protected_fields = ('key', 'item_type', 'service')
