from django.contrib.contenttypes.models import ContentType

from nodeconductor.cost_tracking import models


def make_autocalculate_price_estimate_invisible_on_manual_estimate_creation(sender, instance, created=False, **kwargs):
    if created and instance.is_manually_input:
        manually_created_price_estimate = instance
        (models.PriceEstimate.objects
            .filter(scope=manually_created_price_estimate.scope,
                    year=manually_created_price_estimate.year,
                    month=manually_created_price_estimate.month,
                    is_manually_input=False)
            .update(is_visible=False))


def make_autocalculated_price_estimate_visible_on_manual_estimate_deletion(sender, instance, **kwargs):
    deleted_price_estimate = instance
    if deleted_price_estimate.is_manually_input:
        (models.PriceEstimate.objects
            .filter(scope=deleted_price_estimate.scope,
                    year=deleted_price_estimate.year,
                    month=deleted_price_estimate.month,
                    is_manually_input=False)
            .update(is_visible=True))


def make_autocalculate_price_estimate_invisible_if_manually_created_estimate_exists(
        sender, instance, created=False, **kwargs):
    if created and not instance.is_manually_input:
        if models.PriceEstimate.objects.filter(
                year=instance.year, scope=instance.scope, month=instance.month, is_manually_input=True).exists():
            instance.is_visible = False


def create_price_list_items_for_service(sender, instance, created=False, **kwargs):
    if created:
        service = instance
        service_content_type = ContentType.objects.get_for_model(service)
        for default_item in models.DefaultPriceListItem.objects.filter(service_content_type=service_content_type):
            models.PriceListItem.objects.create(
                service=service,
                key=default_item.key,
                item_type=default_item.item_type,
                value=default_item.value,
                units=default_item.units,
            )


def change_price_list_items_if_default_was_changed(sender, instance, created=False, **kwargs):
    default_item = instance
    if created:
        # if new default item added - we create such item in for each service
        model = default_item.service_content_type.model_class()
        for service in model.objects.all():
            models.PriceListItem.objects.create(
                service=service,
                key=default_item.key,
                item_type=default_item.item_type,
                units=default_item.units,
                value=default_item.value
            )
    else:
        if default_item.tracker.has_changed('key') or default_item.tracker.has_changed('item_type'):
            # if default item key or item type was changed - it will be changed in each connected item
            connected_items = models.PriceListItem.objects.filter(
                key=default_item.tracker.previous('key'),
                item_type=default_item.tracker.previous('item_type'),
                content_type=default_item.service_content_type,
            )
        else:
            # if default value or units changed - it will be changed in each connected item
            # that was not edited manually
            connected_items = models.PriceListItem.objects.filter(
                key=default_item.key,
                item_type=default_item.item_type,
                content_type=default_item.service_content_type,
                is_manually_input=False,
            )
        connected_items.update(
            key=default_item.key, item_type=default_item.item_type, units=default_item.units, value=default_item.value)


def delete_price_list_items_if_default_was_deleted(sender, instance, **kwargs):
    default_item = instance
    models.PriceListItem.objects.filter(
        key=default_item.tracker.previous('key'),
        item_type=default_item.tracker.previous('item_type'),
        content_type=default_item.service_content_type,
    ).delete()
