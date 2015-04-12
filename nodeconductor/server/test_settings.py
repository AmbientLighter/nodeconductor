# Django test settings for nodeconductor project.
from nodeconductor.server.base_settings import *

SECRET_KEY = 'test-key'

DEBUG = True
TEMPLATE_DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

INSTALLED_APPS += (
    'kombu.transport.django',  # Needed for broker backend
    'djcelery',  # Needed for result backend
    'test_without_migrations',  # To run tests without migrations
)

BROKER_URL = 'django://'
CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend'

NODECONDUCTOR = {
    'OPENSTACK_CREDENTIALS': (
        {
            'auth_url': 'http://example.com:5000/v2',
            'username': 'admin',
            'password': 'password',
            'tenant_name': 'admin',
        },
    ),
    'MONITORING': {
        'ZABBIX': {
            'server': "http://127.0.0.1:8888/zabbix",
            'username': "admin",
            'password': "zabbix",

            'interface_parameters': {"ip": "0.0.0.0", "main": 1, "port": "10050", "type": 1, "useip": 1, "dns": ""},
            'templateid': '10106',
            'groupid': '8',
            'default_service_parameters': {'algorithm': 1, 'showsla': 1, 'sortorder': 1, 'goodsla': 95},
        }
    }
}
