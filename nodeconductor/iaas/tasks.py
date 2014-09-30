# coding: utf-8
from __future__ import absolute_import, unicode_literals

import functools
import logging

from celery import shared_task
from django_fsm import TransitionNotAllowed
from django.db import transaction, DatabaseError
import six

from nodeconductor.iaas import models

logger = logging.getLogger(__name__)


class StateChangeError(RuntimeError):
    pass


# XXX: Deprecated
class BackgroundProcessingException(Exception):
    pass


def _mock_processing(instance_uuid, should_fail=False):
    if should_fail:
        raise BackgroundProcessingException('It\'s not my day')

    import time
    time.sleep(10)

    # update some values
    with transaction.atomic():
        try:
            instance = models.Instance.objects.get(uuid=instance_uuid)
            instance.ips = '1.2.3.4, 10.10.10.10'
            instance.save()
        except models.Instance.DoesNotExist:
            raise BackgroundProcessingException('Error updating VM instance')


# TODO: Convert the code to use @tracked_processing
def _schedule_instance_operation(instance_uuid, operation, processing_callback):
    logger.info('About to %s instance with uuid %s' % (operation, instance_uuid))
    supported_operations = {
        'provisioning': ('provisioning', 'online'),
        'deleting': ('deleting', 'deleted'),
        'starting': ('starting', 'online'),
        'stopping': ('stopping', 'offline'),
    }

    with transaction.atomic():
        try:
            instance = models.Instance.objects.get(uuid=instance_uuid)
        except models.Instance.DoesNotExist:
            logger.error('Could not find instance with uuid %s to schedule %s for' % (instance_uuid, operation))
            # There's nothing we can do here to save the state of an instance
            return

        try:
            # mark start of the transition
            getattr(instance, supported_operations[operation][0])()
            instance.save()
        except TransitionNotAllowed:
            logger.warn('Transition from state %s using operation %s is not allowed'
                        % (instance.get_state_display(), operation))
            # Leave the instance intact
            return

    try:
        processing_callback(instance_uuid)
    except BackgroundProcessingException as e:
        with transaction.atomic():
            try:
                instance = models.Instance.objects.get(uuid=instance_uuid)
            except models.Instance.DoesNotExist:
                logger.error('Could not find instance with uuid %s to mark as erred while running %s'
                             % (instance_uuid, operation))
                # There's nothing we can do here to save the state of an instance
                return

            logger.error('Error while performing instance %s operation %s: %s' % (instance_uuid, operation, e))
            instance.erred()
            instance.save()
            return

    # We need to get the fresh instance from db so that presentation layer
    # property changes would not get lost
    with transaction.atomic():
        try:
            instance = models.Instance.objects.get(uuid=instance_uuid)
        except models.Instance.DoesNotExist:
            logger.error('Instance with uuid %s has gone away during %s' % (instance_uuid, operation))

            # There's nothing we can do here to save the state of an instance
            return

        getattr(instance, supported_operations[operation][1])()
        instance.save()


# noinspection PyProtectedMember
def set_state(model_class, uuid, transition):
    """
    Atomically change state of a model_class instance.

    Handles edge cases:
    * model instance missing in the database
    * concurrent database update of a model instance
    * model instance being in a state that forbids transition

    Raises StateChangeError in case of any of the above.

    Example:

    .. code-block:: python
        # models.py
        from django.db import
        from nodeconductor.core.models import UuidMixin

        class Worker(UuidMixin, models.Model):
            state = FSMField(default='idle')

            @transition(field=state, source='idle', target='working')
            def start_working(self):
                pass

        # views.py
        from django.shortcuts import render_to_response
        from . import models

        def begin_work(worker_uuid):
            try:
                set_state(models.Worker, worker_uuid, 'start_working')
            except StateChangeError:
                return render_to_response('failed to start working')
            else:
                return render_to_response('started working')

    :param model_class: model class of an instance to change state
    :type model_class: django.db.models.Model
    :param uuid: identifier of the model_class instance
    :type uuid: str
    :param transition: name of model's method to trigger transition
    :type transition: str
    :raises: StateChangeError
    """
    logged_operation = transition.replace('_', ' ')
    entity_name = model_class._meta.model_name

    logger.info(
        'About to start %s %s with uuid %s',
        logged_operation, entity_name, uuid
    )

    try:
        with transaction.atomic():
            entity = model_class._default_manager.get(uuid=uuid)

            # TODO: Make sure that the transition method actually exists
            transition = getattr(entity, transition)
            transition()

            entity.save()
    except model_class.DoesNotExist:
        # There's nothing we can do here to save the state of an entity
        logger.error(
            'Could not perform %s %s with uuid, %s has gone',
            logged_operation, entity_name, uuid, entity_name)
        six.reraise(StateChangeError)
    except DatabaseError:
        # Transaction failed to commit, most likely due to concurrent update
        logger.exception(
            'Could not perform %s %s with uuid %s due to concurrent update',
            logged_operation, entity_name, uuid)
        six.reraise(StateChangeError)
    except TransitionNotAllowed:
        # Leave the entity intact
        logger.exception(
            'Could not perform %s %s with uuid %s, transition not allowed',
            logged_operation, entity_name, uuid)
        six.reraise(StateChangeError)

    # TODO: Emit high level event log entry
    logger.info(
        'Managed to finish %s %s with uuid %s',
        logged_operation, entity_name, uuid
    )


def tracked_processing(model_class, processing_state, desired_state, error_state='erred'):
    def decorator(processing_fn):
        @functools.wraps(processing_fn)
        def wrapped(*args, **kwargs):
            # XXX: This is very fragile :(
            try:
                uuid = kwargs['uuid']
            except KeyError:
                uuid = args[0]

            set_entity_state = functools.partial(set_state, model_class, uuid)

            try:
                set_entity_state(processing_state)

                # We should handle all exceptions here so that processing
                # can concentrate on positive flow

                # noinspection PyBroadException
                try:
                    processing_fn(*args, **kwargs)
                except Exception:
                    # noinspection PyProtectedMember
                    logger.exception(
                        'Failed to finish %s %s with uuid %s',
                        processing_state, model_class._meta.model_name, uuid
                    )

                    set_entity_state(error_state)
                else:
                    set_entity_state(desired_state)
            except StateChangeError:
                # No logging is needed since set_state already logged everything
                pass

        return wrapped
    return decorator


@shared_task
@tracked_processing(models.Instance, processing_state='provisioning', desired_state='online')
def schedule_provisioning(instance_uuid):
    _mock_processing(instance_uuid)


@shared_task
def schedule_stopping(instance_uuid):
    _schedule_instance_operation(instance_uuid, 'stopping', _mock_processing)


@shared_task
def schedule_starting(instance_uuid):
    _schedule_instance_operation(instance_uuid, 'starting', _mock_processing)


@shared_task
def schedule_deleting(instance_uuid):
    _schedule_instance_operation(instance_uuid, 'deleting', _mock_processing)
