from nodeconductor.logging.log import EventLogger, event_logger
from nodeconductor.core.models import User, SshPublicKey


class AuthEventLogger(EventLogger):
    user = User

    class Meta:
        event_types = ('auth_logged_in_with_username',
                       'auth_logged_in_with_pki',
                       'auth_logged_out')


class UserEventLogger(EventLogger):
    affected_user = User

    class Meta:
        permitted_objects_uuids = staticmethod(lambda user: {'user_uuid': [user.uuid.hex]})
        event_types = ('user_creation_succeeded',
                       'user_update_succeeded',
                       'user_deletion_succeeded',
                       'user_password_updated',
                       'user_activated',
                       'user_deactivated')


class SshPublicKeyEventLogger(EventLogger):
    ssh_key = SshPublicKey

    class Meta:
        event_types = ('ssh_key_creation_succeeded',
                       'ssh_key_deletion_succeeded')


event_logger.register('auth', AuthEventLogger)
event_logger.register('user', UserEventLogger)
event_logger.register('sshkey', SshPublicKeyEventLogger)


# Backward compatibility imports
from nodeconductor.logging.log import TCPEventHandler, RequireEvent, RequireNotEvent
import warnings


class NodeConductorDeprecationWarning(PendingDeprecationWarning):
    pass


warnings.simplefilter('always', NodeConductorDeprecationWarning)
warnings.warn(
    "TCPEventHandler and RequireEvent/RequireNotEvent classes have been moved to "
    "nodeconductor.logging.log and will be removed from nodeconductor.core.log "
    "in further releases, consider updating your settings",
    NodeConductorDeprecationWarning)
