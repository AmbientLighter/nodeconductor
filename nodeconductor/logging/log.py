import json
import uuid
import types
import decimal
import datetime
import logging

from django.apps import apps
from django.utils import six
from django.contrib.contenttypes import models as ct_models

from nodeconductor.logging import models
from nodeconductor.logging.middleware import get_event_context
from nodeconductor.core.tasks import send_task


logger = logging.getLogger(__name__)


class LoggerError(AttributeError):
    pass


class EventLoggerError(AttributeError):
    pass


class AlertLoggerError(AttributeError):
    pass


class BaseLogger(object):
    def __init__(self, logger_name=__name__):
        self._meta = getattr(self, 'Meta', None)
        self.supported_types = self.get_supported_types()

    def get_supported_types(self):
        raise NotImplemented('Method is not implemented')

    def get_nullable_fields(self):
        return getattr(self._meta, 'nullable_fields', [])

    def compile_message(self, message_template, context):
        try:
            msg = message_template.format(**context)
        except KeyError as e:
            raise LoggerError(
                "Cannot find %s context field. Choices are: %s" % (
                    str(e), ', '.join(context.keys())))
        return msg

    def validate_logging_type(self, logging_type):
        if self.supported_types and logging_type not in self.supported_types:
            raise EventLoggerError(
                "Unsupported logging type '%s'. Choices are: %s" % (
                    logging_type, ', '.join(self.supported_types)))

    def compile_context(self, **kwargs):
        # Get a list of fields here in order to be sure all models already loaded.
        if not hasattr(self, 'fields'):
            self.fields = {
                k: apps.get_model(v) if isinstance(v, basestring) else v
                for k, v in self.__class__.__dict__.items()
                if not k.startswith('_') and not isinstance(v, (types.ClassType, types.FunctionType))}

        context = {}
        required_fields = self.fields.copy()

        event_context = get_event_context()
        if event_context:
            context.update(event_context)
            username = event_context.get('user_username')
            if 'user' in required_fields and username:
                logger.warning("User is passed directly to event context. "
                               "Currently authenticated user %s is ignored.", username)

        for entity_name, entity in six.iteritems(kwargs):
            if entity_name in required_fields:
                entity_class = required_fields.pop(entity_name)
                if entity is None and entity_name in self.get_nullable_fields():
                    continue
                if not isinstance(entity, entity_class):
                    raise LoggerError(
                        "Field '%s' must be an instance of %s but %s received" % (
                            entity_name, entity_class.__name__, entity.__class__.__name__))
            else:
                logger.error(
                    "Field '%s' cannot be used in logging context for %s",
                    entity_name, self.__class__.__name__)
                continue

            if isinstance(entity, LoggableMixin):
                context.update(entity._get_log_context(entity_name))
            elif isinstance(entity, (int, float, basestring, dict, tuple, list, bool)):
                context[entity_name] = entity
            elif entity is None:
                pass
            else:
                context[entity_name] = six.text_type(entity)
                logger.warning(
                    "Cannot properly serialize '%s' context field. "
                    "Must be inherited from LoggableMixin." % entity_name)

        if required_fields:
            raise LoggerError(
                "Missed fields in event context: %s" % ', '.join(required_fields.keys()))

        return context


class EventLogger(BaseLogger):
    """ Base event logger API.
        Fields which must be passed during event log emitting (event context)
        should be defined as attributes for this class in the form of:

        field_name = ObjectClass || '<app_label>.<class_name>'

        A list of supported event types can be defined with help of method get_supported_types,
        or 'event_types' property of Meta class. Event type won't be validated if this list is empty.

        Example usage:

        .. code-block:: python

            from nodeconductor.iaas.models import Cloud

            class QuotaEventLogger(EventLogger):
                cloud_account = Cloud
                project = 'structure.Project'
                threshold = float
                quota_type = basestring

                class Meta:
                    event_types = 'quota_threshold_reached',


            quota_logger = QuotaEventLogger(__name__)
            quota_logger.warning(
                '{quota_type} quota threshold has been reached for {project_name}.',
                event_type='quota_threshold_reached',
                event_context=dict(
                    quota_type=quota.name,
                    project=membership.project,
                    cloud_account=membership.cloud,
                    threshold=threshold * quota.limit)
            )
    """

    def __init__(self, logger_name=__name__):
        super(EventLogger, self).__init__(logger_name)
        self.logger = EventLoggerAdapter(logging.getLogger(logger_name))

    def get_supported_types(self):
        return getattr(self._meta, 'event_types', tuple())

    def info(self, *args, **kwargs):
        self.process('info', *args, **kwargs)

    def error(self, *args, **kwargs):
        self.process('error', *args, **kwargs)

    def warning(self, *args, **kwargs):
        self.process('warning', *args, **kwargs)

    def debug(self, *args, **kwargs):
        self.process('debug', *args, **kwargs)

    def process(self, level, message_template, event_type='undefined', event_context=None):
        self.validate_logging_type(event_type)

        if not event_context:
            event_context = {}

        context = self.compile_context(**event_context)
        msg = self.compile_message(message_template, context)

        log = getattr(self.logger, level)
        log(msg, extra={'event_type': event_type, 'event_context': context})


class AlertLogger(BaseLogger):
    """ Base alert logger API.

        Fields which must be passed during alert log emitting (alert context)
        should be defined as attributes for this class in the form of:

        field_name = ObjectClass || '<app_label>.<class_name>'

        A list of supported event types can be defined with help of method get_supported_types,
        or 'alert_types' property of Meta class. Event type won't be validated if this list is empty.

        Example usage:

        .. code-block:: python

            from nodeconductor.logging.log import AlertLogger, alert_logger
            from nodeconductor.quotas import models

            class QuotaAlertLogger(AlertLogger):
                quota = models.Quota

                class Meta:
                    alert_types = ('quota_usage_is_over_threshold', )

            alert_logger.register('quota', QuotaAlertLogger)


            alert_logger.quota.warning(
                'Quota {quota_name} is over threshold. Limit: {quota_limit}, usage: {quota_usage}',
                scope=quota,
                alert_type='quota_usage_is_over_threshold',
                alert_context={
                    'quota': quota
                })
    """

    def get_supported_types(self):
        return getattr(self._meta, 'alert_types', tuple())

    def info(self, *args, **kwargs):
        self.process(models.Alert.SeverityChoices.INFO, *args, **kwargs)

    def error(self, *args, **kwargs):
        self.process(models.Alert.SeverityChoices.ERROR, *args, **kwargs)

    def warning(self, *args, **kwargs):
        self.process(models.Alert.SeverityChoices.WARNING, *args, **kwargs)

    def debug(self, *args, **kwargs):
        self.process(models.Alert.SeverityChoices.DEBUG, *args, **kwargs)

    def process(self, severity, message_template, scope, alert_type='undefined', alert_context=None):
        self.validate_logging_type(alert_type)

        if not alert_context:
            alert_context = {}

        context = self.compile_context(**alert_context)
        msg = self.compile_message(message_template, context)
        try:
            content_type = ct_models.ContentType.objects.get_for_model(scope)
            alert = models.Alert.objects.get(
                object_id=scope.id, content_type=content_type, alert_type=alert_type, closed__isnull=True)
            if alert.severity != severity or alert.message != msg:
                alert.severity = severity
                alert.message = msg
                alert.save()
            created = False
        except models.Alert.DoesNotExist:
            alert = models.Alert.objects.create(
                alert_type=alert_type, message=msg, severity=severity, context=context, scope=scope)
            created = True

        return alert, created

    def close(self, scope, alert_type):
        try:
            content_type = ct_models.ContentType.objects.get_for_model(scope)
            alert = models.Alert.objects.get(
                object_id=scope.id, content_type=content_type, alert_type=alert_type, closed__isnull=True)
            alert.close()
        except models.Alert.DoesNotExist:
            pass


class LoggableMixin(object):
    """ Mixin to serialize model in logs.
        Extends django model or custom class with fields extraction method.
    """

    def get_log_fields(self):
        return ('uuid', 'name')

    def _get_log_context(self, entity_name):

        context = {}
        for field in self.get_log_fields():
            if not hasattr(self, field):
                continue

            value = getattr(self, field)

            name = "{}_{}".format(entity_name, field)
            if isinstance(value, uuid.UUID):
                context[name] = value.hex
            elif isinstance(value, LoggableMixin):
                context.update(value._get_log_context(field))
            elif isinstance(value, datetime.date):
                context[name] = value.isoformat()
            elif isinstance(value, decimal.Decimal):
                context[name] = float(value)
            else:
                context[name] = six.text_type(value)

        return context

    @classmethod
    def get_permitted_objects_uuids(self, user):
        return {}


class EventFormatter(logging.Formatter):

    def format_timestamp(self, time):
        return datetime.datetime.utcfromtimestamp(time).isoformat() + 'Z'

    def levelname_to_importance(self, levelname):
        if levelname == 'DEBUG':
            return 'low'
        elif levelname == 'INFO':
            return 'normal'
        elif levelname == 'WARNING':
            return 'high'
        elif levelname == 'ERROR':
            return 'very high'
        else:
            return 'critical'

    def format(self, record):
        message = {
            # basic
            '@timestamp': self.format_timestamp(record.created),
            '@version': 1,
            'message': record.getMessage(),

            # logging details
            'levelname': record.levelname,
            'logger': record.name,
            'importance': self.levelname_to_importance(record.levelname),
            'importance_code': record.levelno,
        }

        if hasattr(record, 'event_type'):
            message['event_type'] = record.event_type

        if hasattr(record, 'event_context'):
            message.update(record.event_context)

        return json.dumps(message)


class EventLoggerAdapter(logging.LoggerAdapter, object):
    """ LoggerAdapter """

    def __init__(self, logger):
        super(EventLoggerAdapter, self).__init__(logger, {})

    def process(self, msg, kwargs):
        if 'extra' in kwargs:
            kwargs['extra']['event'] = True
        else:
            kwargs['extra'] = {'event': True}
        return msg, kwargs


class RequireEvent(logging.Filter):
    """ A filter that allows only event records. """

    def filter(self, record):
        return getattr(record, 'event', False)


class RequireNotEvent(logging.Filter):
    """ A filter that allows only non-event records. """

    def filter(self, record):
        return not getattr(record, 'event', False)


class TCPEventHandler(logging.handlers.SocketHandler, object):

    def __init__(self, host='localhost', port=5959):
        super(TCPEventHandler, self).__init__(host, int(port))
        self.formatter = EventFormatter()

    def makePickle(self, record):
        return self.formatter.format(record) + b'\n'


class HookHandler(logging.Handler):
    def emit(self, record):
        # Check that record contains event
        if hasattr(record, 'event_type') and hasattr(record, 'event_context'):

            # Convert record to plain dictionary
            event = {
                'timestamp': record.created,
                'levelname': record.levelname,
                'message': record.getMessage(),
                'type': record.event_type,
                'context': record.event_context
            }

            if models.BaseHook.has_hooks():
                # Perform hook processing in background thread
                send_task('logging', 'process_event')(event)


class BaseLoggerRegistry(object):

    def get_loggers(self):
        raise NotImplemented('Method "get_loggers" is not implemented.')

    def register(self, name, logger):
        if name in self.__dict__:
            raise EventLoggerError("Logger '%s' already registered." % name)
        self.__dict__[name] = logger() if isinstance(logger, type) else logger


class EventLoggerRegistry(BaseLoggerRegistry):

    def get_loggers(self):
        return [l for l in self.__dict__.values() if isinstance(l, EventLogger)]

    def get_permitted_objects_uuids(self, user):
        from nodeconductor.logging.utils import get_loggable_models
        permitted_objects_uuids = {}
        for model in get_loggable_models():
            permitted_objects_uuids.update(model.get_permitted_objects_uuids(user))
        return permitted_objects_uuids

    def get_permitted_event_types(self):
        events = set()
        for elogger in self.get_loggers():
            events.update(elogger.get_supported_types())
        return events


class AlertLoggerRegistry(BaseLoggerRegistry):

    def get_loggers(self):
        return [l for l in self.__dict__.values() if isinstance(l, AlertLogger)]


# This global objects represent the default loggers registry
event_logger = EventLoggerRegistry()
alert_logger = AlertLoggerRegistry()
