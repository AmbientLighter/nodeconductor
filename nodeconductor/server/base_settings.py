"""
Django base settings for nodeconductor project.
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from datetime import timedelta
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..'))


DEBUG = False

TEMPLATE_DEBUG = False

ALLOWED_HOSTS = []

# Application definition
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'nodeconductor.landing',
    'nodeconductor.events',
    'nodeconductor.core',
    'nodeconductor.backup',
    'nodeconductor.template',
    'nodeconductor.monitoring',
    'nodeconductor.quotas',
    'nodeconductor.structure',
    'nodeconductor.billing',
    'nodeconductor.iaas',
    'nodeconductor.ldapsync',

    'nodeconductor.testdata',

    # Template overrides need to happen before admin is imported.
    'django.contrib.admin',

    'rest_framework',
    'rest_framework.authtoken',

    'permission',
    'django_fsm',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'nodeconductor.events.middleware.CaptureUserMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

REST_FRAMEWORK = {
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'nodeconductor.core.authentication.TokenAuthentication',
        'nodeconductor.core.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': ('rest_framework.filters.DjangoFilterBackend',),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'nodeconductor.core.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_PAGINATION_CLASS': 'nodeconductor.core.pagination.LinkHeaderPagination',
    'PAGE_SIZE': 10,
    'EXCEPTION_HANDLER': 'nodeconductor.core.views.exception_handler',

    # Return native `Date` and `Time` objects in `serializer.data`
    'DATETIME_FORMAT': None,
    'DATE_FORMAT': None,
    'TIME_FORMAT': None,
}

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'permission.backends.PermissionBackend',
    'djangosaml2.backends.Saml2Backend',
)

ANONYMOUS_USER_ID = None

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'nodeconductor', 'templates'),
    os.path.join(BASE_DIR, 'nodeconductor', 'landing', 'templates'),
)

ROOT_URLCONF = 'nodeconductor.server.urls'

AUTH_USER_MODEL = 'core.User'

WSGI_APPLICATION = 'nodeconductor.server.wsgi.application'

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'

SAML_CREATE_UNKNOWN_USER = True

BROKER_URL = 'redis://localhost'
CELERY_RESULT_BACKEND = 'redis://localhost'

CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_RESULT_SERIALIZER = 'json'

CELERY_QUEUES = {
    'tasks': {'exchange': 'tasks'},
    'heavy': {'exchange': 'heavy'},
}
CELERY_DEFAULT_QUEUE = 'tasks'
CELERY_ROUTES = ('nodeconductor.server.celery.PriorityRouter',)

# Regular tasks
CELERYBEAT_SCHEDULE = {
    'update-instance-monthly-slas': {
        'task': 'nodeconductor.monitoring.tasks.update_instance_sla',
        'schedule': timedelta(minutes=5),
        'args': ('monthly',),
    },
    'update-instance-yearly-slas': {
        'task': 'nodeconductor.monitoring.tasks.update_instance_sla',
        'schedule': timedelta(minutes=10),
        'args': ('yearly',),
    },

    'sync-services': {
        'task': 'nodeconductor.iaas.sync_services',
        'schedule': timedelta(minutes=60),
        'args': (),
    },

    'recover-erred-services': {
        'task': 'nodeconductor.iaas.recover_erred_services',
        'schedule': timedelta(minutes=5),
        'args': (),
    },

    'pull-service-statistics': {
        'task': 'nodeconductor.iaas.tasks.iaas.pull_service_statistics',
        'schedule': timedelta(minutes=15),
        'args': (),
    },
    'pull-cloud-project-memberships': {
        'task': 'nodeconductor.iaas.tasks.iaas.pull_cloud_memberships',
        'schedule': timedelta(minutes=30),
        'args': (),
    },

    'check-cloud-project-memberships-quotas': {
        'task': 'nodeconductor.iaas.tasks.iaas.check_cloud_memberships_quotas',
        'schedule': timedelta(minutes=1440),
        'args': (),
    },

    'recover-erred-cloud-project-memberships': {
        'task': 'nodeconductor.iaas.tasks.iaas.recover_erred_cloud_memberships',
        'schedule': timedelta(minutes=5),
        'args': (),
    },

    'sync-instances-with-zabbix': {
        'task': 'nodeconductor.iaas.tasks.iaas.sync_instances_with_zabbix',
        'schedule': timedelta(minutes=30),
        'args': (),
    },

    'execute-backup-schedules': {
        'task': 'nodeconductor.backup.tasks.execute_schedules',
        'schedule': timedelta(minutes=10),
        'args': (),
    },

    'delete-expired-backups': {
        'task': 'nodeconductor.backup.tasks.delete_expired_backups',
        'schedule': timedelta(minutes=10),
        'args': (),
    }
}

CELERY_TASK_THROTTLING = {
    'nodeconductor.iaas.tasks.openstack.openstack_provision_instance': {
        'concurrency': 1,
        'retry_delay': 30,
    },
}

NODECONDUCTOR = {
    'DEFAULT_SECURITY_GROUPS': (
        {
            'name': 'ssh',
            'description': 'Security group for secure shell access and ping',
            'rules': (
                {
                    'protocol': 'tcp',
                    'cidr': '0.0.0.0/0',
                    'from_port': 22,
                    'to_port': 22,
                },
                {
                    'protocol': 'icmp',
                    'cidr': '0.0.0.0/0',
                    'icmp_type': -1,
                    'icmp_code': -1,
                },
            ),
        },
    ),
    'ELASTICSEARCH_DUMMY': True,
    'JIRA_DUMMY': True,
}
