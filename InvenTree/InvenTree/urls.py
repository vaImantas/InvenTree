"""Top-level URL lookup for InvenTree application.

Passes URL lookup downstream to each app as required.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import RedirectView

from dj_rest_auth.registration.views import (ConfirmEmailView,
                                             SocialAccountDisconnectView,
                                             SocialAccountListView)
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView
from sesame.views import LoginView

from build.api import build_api_urls
from build.urls import build_urls
from common.api import admin_api_urls, common_api_urls, settings_api_urls
from common.urls import common_urls
from company.api import company_api_urls
from company.urls import (company_urls, manufacturer_part_urls,
                          supplier_part_urls)
from label.api import label_api_urls
from order.api import order_api_urls
from order.urls import order_urls
from part.api import bom_api_urls, part_api_urls
from part.urls import part_urls
from plugin.api import plugin_api_urls
from plugin.urls import get_plugin_urls
from report.api import report_api_urls
from stock.api import stock_api_urls
from stock.urls import stock_urls
from users.api import user_urls
from web.urls import spa_view
from web.urls import urlpatterns as platform_urls

from .api import APISearchView, InfoView, NotFoundView
from .magic_login import GetSimpleLoginView
from .social_auth_urls import SocialProvierListView, social_auth_urlpatterns
from .views import (AboutView, AppearanceSelectView, CustomConnectionsView,
                    CustomEmailView, CustomLoginView,
                    CustomPasswordResetFromKeyView,
                    CustomSessionDeleteOtherView, CustomSessionDeleteView,
                    DatabaseStatsView, DynamicJsView, EditUserView, IndexView,
                    NotificationsView, SearchView, SetPasswordView,
                    SettingsView, auth_request)

admin.site.site_header = "InvenTree Admin"


apipatterns = [

    # Global search
    path('search/', APISearchView.as_view(), name='api-search'),

    re_path(r'^settings/', include(settings_api_urls)),
    re_path(r'^part/', include(part_api_urls)),
    re_path(r'^bom/', include(bom_api_urls)),
    re_path(r'^company/', include(company_api_urls)),
    re_path(r'^stock/', include(stock_api_urls)),
    re_path(r'^build/', include(build_api_urls)),
    re_path(r'^order/', include(order_api_urls)),
    re_path(r'^label/', include(label_api_urls)),
    re_path(r'^report/', include(report_api_urls)),
    re_path(r'^user/', include(user_urls)),
    re_path(r'^admin/', include(admin_api_urls)),

    # Plugin endpoints
    path('', include(plugin_api_urls)),

    # Common endpoints endpoint
    path('', include(common_api_urls)),

    # OpenAPI Schema
    re_path('schema/', SpectacularAPIView.as_view(custom_settings={'SCHEMA_PATH_PREFIX': '/api/'}), name='schema'),

    # InvenTree information endpoint
    path('', InfoView.as_view(), name='api-inventree-info'),

    # Auth API endpoints
    path('auth/', include([
        re_path(r'^registration/account-confirm-email/(?P<key>[-:\w]+)/$', ConfirmEmailView.as_view(), name='account_confirm_email'),
        path('registration/', include('dj_rest_auth.registration.urls')),
        path('providers/', SocialProvierListView.as_view(), name='social_providers'),
        path('social/', include(social_auth_urlpatterns)),
        path('social/', SocialAccountListView.as_view(), name='social_account_list'),
        path('social/<int:pk>/disconnect/', SocialAccountDisconnectView.as_view(), name='social_account_disconnect'),
        path('', include('dj_rest_auth.urls')),
    ])),

    # Magic login URLs
    path("email/generate/", csrf_exempt(GetSimpleLoginView().as_view()), name="sesame-generate",),
    path("email/login/", LoginView.as_view(), name="sesame-login"),

    # Unknown endpoint
    re_path(r'^.*$', NotFoundView.as_view(), name='api-404'),
]

settings_urls = [

    re_path(r'^i18n/?', include('django.conf.urls.i18n')),

    re_path(r'^appearance/?', AppearanceSelectView.as_view(), name='settings-appearance'),

    # Catch any other urls
    re_path(r'^.*$', SettingsView.as_view(template_name='InvenTree/settings/settings.html'), name='settings'),
]

notifications_urls = [

    # Catch any other urls
    re_path(r'^.*$', NotificationsView.as_view(), name='notifications'),
]

# These javascript files are served "dynamically" - i.e. rendered on demand
dynamic_javascript_urls = [
    re_path(r'^calendar.js', DynamicJsView.as_view(template_name='js/dynamic/calendar.js'), name='calendar.js'),
    re_path(r'^nav.js', DynamicJsView.as_view(template_name='js/dynamic/nav.js'), name='nav.js'),
    re_path(r'^permissions.js', DynamicJsView.as_view(template_name='js/dynamic/permissions.js'), name='permissions.js'),
    re_path(r'^settings.js', DynamicJsView.as_view(template_name='js/dynamic/settings.js'), name='settings.js'),
]

# These javascript files are passed through the Django translation layer
translated_javascript_urls = [
    re_path(r'^api.js', DynamicJsView.as_view(template_name='js/translated/api.js'), name='api.js'),
    re_path(r'^attachment.js', DynamicJsView.as_view(template_name='js/translated/attachment.js'), name='attachment.js'),
    re_path(r'^barcode.js', DynamicJsView.as_view(template_name='js/translated/barcode.js'), name='barcode.js'),
    re_path(r'^bom.js', DynamicJsView.as_view(template_name='js/translated/bom.js'), name='bom.js'),
    re_path(r'^build.js', DynamicJsView.as_view(template_name='js/translated/build.js'), name='build.js'),
    re_path(r'^charts.js', DynamicJsView.as_view(template_name='js/translated/charts.js'), name='charts.js'),
    re_path(r'^company.js', DynamicJsView.as_view(template_name='js/translated/company.js'), name='company.js'),
    re_path(r'^filters.js', DynamicJsView.as_view(template_name='js/translated/filters.js'), name='filters.js'),
    re_path(r'^forms.js', DynamicJsView.as_view(template_name='js/translated/forms.js'), name='forms.js'),
    re_path(r'^helpers.js', DynamicJsView.as_view(template_name='js/translated/helpers.js'), name='helpers.js'),
    re_path(r'^index.js', DynamicJsView.as_view(template_name='js/translated/index.js'), name='index.js'),
    re_path(r'^label.js', DynamicJsView.as_view(template_name='js/translated/label.js'), name='label.js'),
    re_path(r'^model_renderers.js', DynamicJsView.as_view(template_name='js/translated/model_renderers.js'), name='model_renderers.js'),
    re_path(r'^modals.js', DynamicJsView.as_view(template_name='js/translated/modals.js'), name='modals.js'),
    re_path(r'^order.js', DynamicJsView.as_view(template_name='js/translated/order.js'), name='order.js'),
    re_path(r'^part.js', DynamicJsView.as_view(template_name='js/translated/part.js'), name='part.js'),
    re_path(r'^purchase_order.js', DynamicJsView.as_view(template_name='js/translated/purchase_order.js'), name='purchase_order.js'),
    re_path(r'^return_order.js', DynamicJsView.as_view(template_name='js/translated/return_order.js'), name='return_order.js'),
    re_path(r'^report.js', DynamicJsView.as_view(template_name='js/translated/report.js'), name='report.js'),
    re_path(r'^sales_order.js', DynamicJsView.as_view(template_name='js/translated/sales_order.js'), name='sales_order.js'),
    re_path(r'^search.js', DynamicJsView.as_view(template_name='js/translated/search.js'), name='search.js'),
    re_path(r'^stock.js', DynamicJsView.as_view(template_name='js/translated/stock.js'), name='stock.js'),
    re_path(r'^status_codes.js', DynamicJsView.as_view(template_name='js/translated/status_codes.js'), name='status_codes.js'),
    re_path(r'^plugin.js', DynamicJsView.as_view(template_name='js/translated/plugin.js'), name='plugin.js'),
    re_path(r'^pricing.js', DynamicJsView.as_view(template_name='js/translated/pricing.js'), name='pricing.js'),
    re_path(r'^news.js', DynamicJsView.as_view(template_name='js/translated/news.js'), name='news.js'),
    re_path(r'^tables.js', DynamicJsView.as_view(template_name='js/translated/tables.js'), name='tables.js'),
    re_path(r'^table_filters.js', DynamicJsView.as_view(template_name='js/translated/table_filters.js'), name='table_filters.js'),
    re_path(r'^notification.js', DynamicJsView.as_view(template_name='js/translated/notification.js'), name='notification.js'),
]

backendpatterns = [
    # "Dynamic" javascript files which are rendered using InvenTree templating.
    re_path(r'^js/dynamic/', include(dynamic_javascript_urls)),
    re_path(r'^js/i18n/', include(translated_javascript_urls)),

    re_path(r'^auth/', include('rest_framework.urls', namespace='rest_framework')),
    re_path(r'^auth/?', auth_request),

    re_path(r'^api/', include(apipatterns)),
    re_path(r'^api-doc/', SpectacularRedocView.as_view(url_name='schema'), name='api-doc'),
]

classic_frontendpatterns = [

    # Apps
    re_path(r'^build/', include(build_urls)),
    re_path(r'^common/', include(common_urls)),
    re_path(r'^company/', include(company_urls)),
    re_path(r'^order/', include(order_urls)),
    re_path(r'^manufacturer-part/', include(manufacturer_part_urls)),
    re_path(r'^part/', include(part_urls)),
    re_path(r'^stock/', include(stock_urls)),
    re_path(r'^supplier-part/', include(supplier_part_urls)),

    re_path(r'^edit-user/', EditUserView.as_view(), name='edit-user'),
    re_path(r'^set-password/', SetPasswordView.as_view(), name='set-password'),

    re_path(r'^index/', IndexView.as_view(), name='index'),
    re_path(r'^notifications/', include(notifications_urls)),
    re_path(r'^search/', SearchView.as_view(), name='search'),
    re_path(r'^settings/', include(settings_urls)),
    re_path(r'^about/', AboutView.as_view(), name='about'),
    re_path(r'^stats/', DatabaseStatsView.as_view(), name='stats'),

    # admin sites
    re_path(f'^{settings.INVENTREE_ADMIN_URL}/error_log/', include('error_report.urls')),
    re_path(f'^{settings.INVENTREE_ADMIN_URL}/', admin.site.urls, name='inventree-admin'),

    # DB user sessions
    path('accounts/sessions/other/delete/', view=CustomSessionDeleteOtherView.as_view(), name='session_delete_other', ),
    re_path(r'^accounts/sessions/(?P<pk>\w+)/delete/$', view=CustomSessionDeleteView.as_view(), name='session_delete', ),

    # Single Sign On / allauth
    # overrides of urlpatterns
    re_path(r'^accounts/email/', CustomEmailView.as_view(), name='account_email'),
    re_path(r'^accounts/social/connections/', CustomConnectionsView.as_view(), name='socialaccount_connections'),
    re_path(r"^accounts/password/reset/key/(?P<uidb36>[0-9A-Za-z]+)-(?P<key>.+)/$", CustomPasswordResetFromKeyView.as_view(), name="account_reset_password_from_key"),

    # Override login page
    re_path("accounts/login/", CustomLoginView.as_view(), name="account_login"),

    re_path(r'^accounts/', include('allauth_2fa.urls')),    # MFA support
    re_path(r'^accounts/', include('allauth.urls')),        # included urlpatterns
]


new_frontendpatterns = [
    # Platform urls
    re_path(r'^platform/', include(platform_urls)),
    re_path(r'^platform', spa_view, name='platform'),
]

# Load patterns for frontend according to settings
frontendpatterns = []
if settings.ENABLE_CLASSIC_FRONTEND:
    frontendpatterns.append(re_path('', include(classic_frontendpatterns)))
if settings.ENABLE_PLATFORM_FRONTEND:
    frontendpatterns.append(re_path('', include(new_frontendpatterns)))


# Append custom plugin URLs (if plugin support is enabled)
if settings.PLUGINS_ENABLED:
    frontendpatterns.append(get_plugin_urls())

urlpatterns = [
    re_path('', include(frontendpatterns)),
    re_path('', include(backendpatterns)),
]

# Server running in "DEBUG" mode?
if settings.DEBUG:
    # Static file access
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Media file access
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Debug toolbar access (only allowed in DEBUG mode)
    if settings.DEBUG_TOOLBAR_ENABLED:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns

# Send any unknown URLs to the parts page
urlpatterns += [re_path(r'^.*$', RedirectView.as_view(url='/index/', permanent=False), name='index')]
