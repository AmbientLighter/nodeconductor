from __future__ import unicode_literals

from django.apps import AppConfig
from django.db.models import signals


class QuotasConfig(AppConfig):
    """
    Quotas - objects resource limits and their usage.
    Quotas limits can be editable by users.
    """
    name = 'nodeconductor.quotas'
    verbose_name = 'Quotas'

    def ready(self):
        from nodeconductor.quotas import handlers, utils

        Quota = self.get_model('Quota')

        for index, model in enumerate(utils.get_models_with_quotas()):
            signals.post_save.connect(
                handlers.increase_global_quota,
                sender=model,
                dispatch_uid='nodeconductor.quotas.handlers.increase_global_quota_%s_%s' % (model.__name__, index)
            )

            signals.post_delete.connect(
                handlers.decrease_global_quota,
                sender=model,
                dispatch_uid='nodeconductor.quotas.handlers.decrease_global_quota_%s_%s' % (model.__name__, index)
            )

        signals.post_migrate.connect(
            handlers.create_global_quotas,
            dispatch_uid="nodeconductor.quotas.handlers.create_global_quotas",
        )

        # new quotas
        from nodeconductor.quotas import fields

        for model_index, model in enumerate(utils.get_models_with_quotas()):
            # quota initialization
            signals.post_save.connect(
                handlers.init_quotas,
                sender=model,
                dispatch_uid='nodeconductor.quotas.init_quotas_%s_%s' % (model.__name__, model_index)
            )

            # Counter quota signals
            # How it works:
            # Each counter quota field has list of target models. Change of target model should increase or decrease
            # counter quota. So we connect generated handler to each of target models.
            for counter_field in model.get_quotas_fields(field_class=fields.CounterQuotaField):
                self.register_counter_field_signals(model, counter_field)

        # Aggregator quotas signals
        signals.post_save.connect(
            handlers.handle_aggregated_quotas,
            sender=Quota,
            dispatch_uid='nodeconductor.quotas.handle_aggregated_quotas_post_save',
        )

        signals.pre_delete.connect(
            handlers.handle_aggregated_quotas,
            sender=Quota,
            dispatch_uid='nodeconductor.quotas.handle_aggregated_quotas_pre_delete',
        )

    @staticmethod
    def register_counter_field_signals(model, counter_field):
        from nodeconductor.quotas import handlers

        for target_model_index, target_model in enumerate(counter_field.target_models):
            signals.post_save.connect(
                handlers.count_quota_handler_factory(counter_field),
                sender=target_model,
                weak=False,  # saves handler from garbage collector
                dispatch_uid='nodeconductor.quotas.increase_counter_quota_%s_%s_%s_%s_%s' % (
                    model.__name__, model._meta.app_label, counter_field.name, target_model.__name__, target_model_index)
            )

            signals.post_delete.connect(
                handlers.count_quota_handler_factory(counter_field),
                sender=target_model,
                weak=False,  # saves handler from garbage collector
                dispatch_uid='nodeconductor.quotas.decrease_counter_quota_%s_%s_%s_%s_%s' % (
                    model.__name__, model._meta.app_label, counter_field.name, target_model.__name__, target_model_index)
            )
