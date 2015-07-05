from __future__ import unicode_literals

import permission
import pkg_resources

from django.conf import settings
from django.conf.urls import patterns
from django.conf.urls import include
from django.conf.urls import url
from django.contrib import admin
from django.views.generic import TemplateView

from nodeconductor.core.routers import SortedDefaultRouter as DefaultRouter
from nodeconductor.backup import urls as backup_urls
from nodeconductor.billing import urls as billing_urls
from nodeconductor.iaas import urls as iaas_urls
from nodeconductor.logging import urls as logging_urls
from nodeconductor.oracle import urls as oracle_urls
from nodeconductor.quotas import urls as quotas_urls
from nodeconductor.structure import urls as structure_urls
from nodeconductor.support import urls as support_urls
from nodeconductor.template import urls as template_urls


admin.autodiscover()
permission.autodiscover()

router = DefaultRouter()
backup_urls.register_in(router)
billing_urls.register_in(router)
iaas_urls.register_in(router)
logging_urls.register_in(router)
oracle_urls.register_in(router)
quotas_urls.register_in(router)
structure_urls.register_in(router)
support_urls.register_in(router)
template_urls.register_in(router)


urlpatterns = patterns(
    '',
    url(r'^admin/', include(admin.site.urls), name='admin'),
)

if settings.NODECONDUCTOR.get('EXTENSIONS_AUTOREGISTER'):
    for nodeconductor_extension in pkg_resources.iter_entry_points('nodeconductor_extensions'):
        for app in settings.INSTALLED_APPS:
            if nodeconductor_extension.module_name.startswith(app):
                extension_module = nodeconductor_extension.load()
                if hasattr(extension_module, 'register_in'):
                    extension_module.register_in(router)
                if hasattr(extension_module, 'urlpatterns'):
                    urlpatterns += extension_module.urlpatterns
                break

urlpatterns += patterns(
    '',
    url(r'^api/', include(router.urls)),
    url(r'^api/', include('nodeconductor.logging.urls')),
    url(r'^api/', include('nodeconductor.iaas.urls')),
    url(r'^api/', include('nodeconductor.structure.urls')),
    url(r'^api/version/', 'nodeconductor.core.views.version_detail'),
    url(r'^api-auth/password/', 'nodeconductor.core.views.obtain_auth_token'),
    url(r'^api-auth/saml2/', 'nodeconductor.core.views.assertion_consumer_service'),
    url(r'^api-auth/', include('rest_framework.urls',
                               namespace='rest_framework')),
    url(r'^$', TemplateView.as_view(template_name='landing/index.html')),
)


if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
