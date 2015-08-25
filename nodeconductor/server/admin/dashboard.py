from admin_tools.utils import get_admin_site_name
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from fluent_dashboard.dashboard import modules, FluentIndexDashboard
from fluent_dashboard.modules import AppIconList


class CustomIndexDashboard(FluentIndexDashboard):
    """
    Custom index dashboard for admin site.
    """
    title = 'NodeConductor administration'

    def __init__(self, **kwargs):
        FluentIndexDashboard.__init__(self, **kwargs)
        self.children.append(modules.Group(
            title="IaaS",
            display="tabs",
            children=[
                modules.ModelList(
                    title='Network',
                    models=('nodeconductor.iaas.models.FloatingIP',
                            'nodeconductor.iaas.models.IpMapping',
                            'nodeconductor.iaas.models.SecurityGroup',
                            )
                ),
                modules.ModelList(
                    title='Virtual Machine',
                    models=('nodeconductor.iaas.models.Instance',
                            'nodeconductor.iaas.models.InstanceSlaHistory',
                            'nodeconductor.iaas.models.Template',
                            'nodeconductor.iaas.models.TemplateLicense',
                            )
                ),
                modules.ModelList(
                    title='Cloud',
                    models=('nodeconductor.iaas.models.Cloud',
                            'nodeconductor.iaas.models.CloudProjectMembership',
                            'nodeconductor.iaas.models.OpenStackSettings',
                            )
                )
            ]
        ))
        self.children.append(AppIconList(_('Billing'), models=('nodeconductor.billing.models.Invoice',
                                                               'nodeconductor.cost_tracking.*')))
        self.children.append(AppIconList(_('Structure'), models=('nodeconductor.structure.*',)))
        self.children.append(AppIconList(_('Backup'), models=('nodeconductor.backup.*',)))

    def init_with_context(self, context):
        site_name = get_admin_site_name(context)
        self.children.append(modules.LinkList(
            _('Quick links'),
            layout='inline',
            draggable=False,
            deletable=False,
            collapsible=False,
            children=[
                [_('API'), '/api/'],
                [_('Documentation'), 'http://nodeconductor.readthedocs.org/en/stable/'],
                [_('Change password'),
                 reverse('%s:password_change' % site_name)],
                [_('Log out'), reverse('%s:logout' % site_name)],
            ]
        ))
