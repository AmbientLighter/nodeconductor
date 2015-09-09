ADMIN_APPS = (
    'fluent_dashboard',
    'admin_tools',
    'admin_tools.theming',
    'admin_tools.menu',
    'admin_tools.dashboard',
    'django.contrib.admin',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.contrib.messages.context_processors.messages",
    "django.core.context_processors.request",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
)

FLUENT_DASHBOARD_APP_ICONS = {
    'structure/customer': 'system-users.png',
    'structure/servicesettings':  'preferences-other.png',
    'structure/project': 'folder.png',
    'structure/projectgroup': 'folder-bookmark.png',
    'backup/backup': 'document-export-table.png',
    'backup/backupschedule': 'view-resource-calendar.png',
    'billing/invoice': 'help-donate.png',
    'cost_tracking/pricelistitem': 'view-bank-account.png',
    'cost_tracking/priceestimate': 'feed-subscribe.png',
    'cost_tracking/defaultpricelistitem': 'view-calendar-list.png'
}

ADMIN_TOOLS_INDEX_DASHBOARD = 'nodeconductor.server.admin.dashboard.CustomIndexDashboard'
ADMIN_TOOLS_APP_INDEX_DASHBOARD = 'fluent_dashboard.dashboard.FluentAppIndexDashboard'
ADMIN_TOOLS_MENU = 'nodeconductor.server.admin.menu.CustomMenu'

# Should be specified, otherwise all Applications dashboard will be included.
FLUENT_DASHBOARD_APP_GROUPS = ()
