"""Django settings for InvenTree project.

In practice the settings in this file should not be adjusted,
instead settings can be configured in the config.yaml file
located in the top level project directory.

This allows implementation configuration to be hidden from source control,
as well as separate configuration parameters from the more complex
database setup in this file.
"""

import logging
import os
import socket
import sys
from pathlib import Path

import django.conf.locale
import django.core.exceptions
from django.core.validators import URLValidator
from django.http import Http404
from django.utils.translation import gettext_lazy as _

import moneyed
from dotenv import load_dotenv

from InvenTree.config import get_boolean_setting, get_custom_file, get_setting
from InvenTree.sentry import default_sentry_dsn, init_sentry
from InvenTree.version import inventreeApiVersion

from . import config

INVENTREE_NEWS_URL = 'https://inventree.org/news/feed.atom'

# Determine if we are running in "test" mode e.g. "manage.py test"
TESTING = 'test' in sys.argv or 'TESTING' in os.environ

if TESTING:

    # Use a weaker password hasher for testing (improves testing speed)
    PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher',]

    # Enable slow-test-runner
    TEST_RUNNER = 'django_slowtests.testrunner.DiscoverSlowestTestsRunner'
    NUM_SLOW_TESTS = 25

    # Note: The following fix is "required" for docker build workflow
    # Note: 2022-12-12 still unsure why...
    if os.getenv('INVENTREE_DOCKER'):
        # Ensure that sys.path includes global python libs
        site_packages = '/usr/local/lib/python3.9/site-packages'

        if site_packages not in sys.path:
            print("Adding missing site-packages path:", site_packages)
            sys.path.append(site_packages)

# Are environment variables manipulated by tests? Needs to be set by testing code
TESTING_ENV = False

# New requirement for django 3.2+
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# Build paths inside the project like this: BASE_DIR.joinpath(...)
BASE_DIR = config.get_base_dir()

# Load configuration data
CONFIG = config.load_config_data(set_cache=True)

# Load VERSION data if it exists
version_file = BASE_DIR.parent.joinpath('VERSION')
if version_file.exists():
    print('load version from file')
    load_dotenv(version_file)

# Default action is to run the system in Debug mode
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = get_boolean_setting('INVENTREE_DEBUG', 'debug', True)

ENABLE_CLASSIC_FRONTEND = get_boolean_setting('INVENTREE_CLASSIC_FRONTEND', 'classic_frontend', True)
ENABLE_PLATFORM_FRONTEND = get_boolean_setting('INVENTREE_PLATFORM_FRONTEND', 'platform_frontend', True)

# Configure logging settings
log_level = get_setting('INVENTREE_LOG_LEVEL', 'log_level', 'WARNING')

logging.basicConfig(
    level=log_level,
    format="%(asctime)s %(levelname)s %(message)s",
)

if log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
    log_level = 'WARNING'  # pragma: no cover

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': log_level,
    },
    'filters': {
        'require_not_maintenance_mode_503': {
            '()': 'maintenance_mode.logging.RequireNotMaintenanceMode503',
        },
    },
}

# Get a logger instance for this setup file
logger = logging.getLogger("inventree")

# Load SECRET_KEY
SECRET_KEY = config.get_secret_key()

# The filesystem location for served static files
STATIC_ROOT = config.get_static_dir()

# The filesystem location for uploaded meadia files
MEDIA_ROOT = config.get_media_dir()

# List of allowed hosts (default = allow all)
ALLOWED_HOSTS = get_setting(
    "INVENTREE_ALLOWED_HOSTS",
    config_key='allowed_hosts',
    default_value=['*'],
    typecast=list,
)

# Cross Origin Resource Sharing (CORS) options

# Only allow CORS access to API
CORS_URLS_REGEX = r'^/api/.*$'

# Extract CORS options from configuration file
CORS_ORIGIN_ALLOW_ALL = get_boolean_setting(
    "INVENTREE_CORS_ORIGIN_ALLOW_ALL",
    config_key='cors.allow_all',
    default_value=False,
)

CORS_ORIGIN_WHITELIST = get_setting(
    "INVENTREE_CORS_ORIGIN_WHITELIST",
    config_key='cors.whitelist',
    default_value=[],
    typecast=list,
)

# Needed for the parts importer, directly impacts the maximum parts that can be uploaded
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

# Web URL endpoint for served static files
STATIC_URL = '/static/'

STATICFILES_DIRS = []

# Translated Template settings
STATICFILES_I18_PREFIX = 'i18n'
STATICFILES_I18_SRC = BASE_DIR.joinpath('templates', 'js', 'translated')
STATICFILES_I18_TRG = BASE_DIR.joinpath('InvenTree', 'static_i18n')
STATICFILES_DIRS.append(STATICFILES_I18_TRG)
STATICFILES_I18_TRG = STATICFILES_I18_TRG.joinpath(STATICFILES_I18_PREFIX)

STATFILES_I18_PROCESSORS = [
    'InvenTree.context.status_codes',
]

# Color Themes Directory
STATIC_COLOR_THEMES_DIR = STATIC_ROOT.joinpath('css', 'color-themes').resolve()

# Web URL endpoint for served media files
MEDIA_URL = '/media/'

# Database backup options
# Ref: https://django-dbbackup.readthedocs.io/en/master/configuration.html
DBBACKUP_SEND_EMAIL = False
DBBACKUP_STORAGE = get_setting(
    'INVENTREE_BACKUP_STORAGE',
    'backup_storage',
    'django.core.files.storage.FileSystemStorage'
)

# Default backup configuration
DBBACKUP_STORAGE_OPTIONS = get_setting('INVENTREE_BACKUP_OPTIONS', 'backup_options', None)
if DBBACKUP_STORAGE_OPTIONS is None:
    DBBACKUP_STORAGE_OPTIONS = {
        'location': config.get_backup_dir(),
    }

# Application definition

INSTALLED_APPS = [
    # Admin site integration
    'django.contrib.admin',

    # InvenTree apps
    'build.apps.BuildConfig',
    'common.apps.CommonConfig',
    'company.apps.CompanyConfig',
    'plugin.apps.PluginAppConfig',          # Plugin app runs before all apps that depend on the isPluginRegistryLoaded function
    'label.apps.LabelConfig',
    'order.apps.OrderConfig',
    'part.apps.PartConfig',
    'report.apps.ReportConfig',
    'stock.apps.StockConfig',
    'users.apps.UsersConfig',
    'web',
    'generic',
    'InvenTree.apps.InvenTreeConfig',       # InvenTree app runs last

    # Core django modules
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'user_sessions',                # db user sessions
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # Maintenance
    'maintenance_mode',

    # Third part add-ons
    'django_filters',                       # Extended filter functionality
    'rest_framework',                       # DRF (Django Rest Framework)
    'rest_framework.authtoken',             # Token authentication for API
    'corsheaders',                          # Cross-origin Resource Sharing for DRF
    'crispy_forms',                         # Improved form rendering
    'import_export',                        # Import / export tables to file
    'django_cleanup.apps.CleanupConfig',    # Automatically delete orphaned MEDIA files
    'mptt',                                 # Modified Preorder Tree Traversal
    'markdownify',                          # Markdown template rendering
    'djmoney',                              # django-money integration
    'djmoney.contrib.exchange',             # django-money exchange rates
    'error_report',                         # Error reporting in the admin interface
    'django_q',
    'formtools',                            # Form wizard tools
    'dbbackup',                             # Backups - django-dbbackup
    'taggit',                               # Tagging
    'flags',                                # Flagging - django-flags

    'allauth',                              # Base app for SSO
    'allauth.account',                      # Extend user with accounts
    'allauth.socialaccount',                # Use 'social' providers

    'django_otp',                           # OTP is needed for MFA - base package
    'django_otp.plugins.otp_totp',          # Time based OTP
    'django_otp.plugins.otp_static',        # Backup codes

    'allauth_2fa',                          # MFA flow for allauth
    'dj_rest_auth',                         # Authentication APIs - dj-rest-auth
    'dj_rest_auth.registration',            # Registration APIs - dj-rest-auth'
    'drf_spectacular',                      # API documentation

    'django_ical',                          # For exporting calendars
]

MIDDLEWARE = CONFIG.get('middleware', [
    'django.middleware.security.SecurityMiddleware',
    'x_forwarded_for.middleware.XForwardedForMiddleware',
    'user_sessions.middleware.SessionMiddleware',                   # db user sessions
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'InvenTree.middleware.InvenTreeRemoteUserMiddleware',       # Remote / proxy auth
    'django_otp.middleware.OTPMiddleware',                      # MFA support
    'InvenTree.middleware.CustomAllauthTwoFactorMiddleware',    # Flow control for allauth
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'InvenTree.middleware.AuthRequiredMiddleware',
    'InvenTree.middleware.Check2FAMiddleware',                  # Check if the user should be forced to use MFA
    'maintenance_mode.middleware.MaintenanceModeMiddleware',
    'InvenTree.middleware.InvenTreeExceptionProcessor',         # Error reporting
])

AUTHENTICATION_BACKENDS = CONFIG.get('authentication_backends', [
    'django.contrib.auth.backends.RemoteUserBackend',           # proxy login
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',      # SSO login via external providers
    "sesame.backends.ModelBackend",                             # Magic link login django-sesame
])

DEBUG_TOOLBAR_ENABLED = DEBUG and get_setting('INVENTREE_DEBUG_TOOLBAR', 'debug_toolbar', False)

# If the debug toolbar is enabled, add the modules
if DEBUG_TOOLBAR_ENABLED:  # pragma: no cover
    logger.info("Running with DEBUG_TOOLBAR enabled")
    INSTALLED_APPS.append('debug_toolbar')
    MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')

    DEBUG_TOOLBAR_CONFIG = {
        'RESULTS_CACHE_SIZE': 100,
        'OBSERVE_REQUEST_CALLBACK': lambda x: False,
    }

# Internal IP addresses allowed to see the debug toolbar
INTERNAL_IPS = [
    '127.0.0.1',
]

# Internal flag to determine if we are running in docker mode
DOCKER = get_boolean_setting('INVENTREE_DOCKER', default_value=False)

if DOCKER:  # pragma: no cover
    # Internal IP addresses are different when running under docker
    hostname, ___, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS = [ip[: ip.rfind(".")] + ".1" for ip in ips] + ["127.0.0.1", "10.0.2.2"]

# Allow secure http developer server in debug mode
if DEBUG:
    INSTALLED_APPS.append('sslserver')

# InvenTree URL configuration

# Base URL for admin pages (default="admin")
INVENTREE_ADMIN_URL = get_setting(
    'INVENTREE_ADMIN_URL',
    config_key='admin_url',
    default_value='admin'
)

ROOT_URLCONF = 'InvenTree.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR.joinpath('templates'),
            # Allow templates in the reporting directory to be accessed
            MEDIA_ROOT.joinpath('report'),
            MEDIA_ROOT.joinpath('label'),
        ],
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Custom InvenTree context processors
                'InvenTree.context.health_status',
                'InvenTree.context.status_codes',
                'InvenTree.context.user_roles',
            ],
            'loaders': [(
                'InvenTree.template.InvenTreeTemplateLoader', [
                    'plugin.template.PluginTemplateLoader',
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ])
            ],
        },
    },
]

if DEBUG_TOOLBAR_ENABLED:  # pragma: no cover
    # Note that the APP_DIRS value must be set when using debug_toolbar
    # But this will kill template loading for plugins
    TEMPLATES[0]['APP_DIRS'] = True
    del TEMPLATES[0]['OPTIONS']['loaders']

REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'InvenTree.exceptions.exception_handler',
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
        'rest_framework.permissions.DjangoModelPermissions',
        'InvenTree.permissions.RolePermission',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_METADATA_CLASS': 'InvenTree.metadata.InvenTreeMetadata',
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ]
}

if DEBUG:
    # Enable browsable API if in DEBUG mode
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'].append('rest_framework.renderers.BrowsableAPIRenderer')

# dj-rest-auth
# JWT switch
USE_JWT = get_boolean_setting('INVENTREE_USE_JWT', 'use_jwt', False)
REST_USE_JWT = USE_JWT
OLD_PASSWORD_FIELD_ENABLED = True
REST_AUTH_REGISTER_SERIALIZERS = {'REGISTER_SERIALIZER': 'InvenTree.forms.CustomRegisterSerializer'}

# JWT settings - rest_framework_simplejwt
if USE_JWT:
    JWT_AUTH_COOKIE = 'inventree-auth'
    JWT_AUTH_REFRESH_COOKIE = 'inventree-token'
    REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] + (
        'dj_rest_auth.jwt_auth.JWTCookieAuthentication',
    )
    INSTALLED_APPS.append('rest_framework_simplejwt')

# WSGI default setting
SPECTACULAR_SETTINGS = {
    'TITLE': 'InvenTree API',
    'DESCRIPTION': 'API for InvenTree - the intuitive open source inventory management system',
    'LICENSE': {'MIT': 'https://github.com/inventree/InvenTree/blob/master/LICENSE'},
    'EXTERNAL_DOCS': {'docs': 'https://docs.inventree.org', 'web': 'https://inventree.org'},
    'VERSION': inventreeApiVersion(),
    'SERVE_INCLUDE_SCHEMA': False,
}

WSGI_APPLICATION = 'InvenTree.wsgi.application'

"""
Configure the database backend based on the user-specified values.

- Primarily this configuration happens in the config.yaml file
- However there may be reason to configure the DB via environmental variables
- The following code lets the user "mix and match" database configuration
"""

logger.debug("Configuring database backend:")

# Extract database configuration from the config.yaml file
db_config = CONFIG.get('database', {})

if not db_config:
    db_config = {}

# Environment variables take preference over config file!

db_keys = ['ENGINE', 'NAME', 'USER', 'PASSWORD', 'HOST', 'PORT']

for key in db_keys:
    # First, check the environment variables
    env_key = f"INVENTREE_DB_{key}"
    env_var = os.environ.get(env_key, None)

    if env_var:
        # Make use PORT is int
        if key == 'PORT':
            try:
                env_var = int(env_var)
            except ValueError:
                logger.error(f"Invalid number for {env_key}: {env_var}")
        # Override configuration value
        db_config[key] = env_var

# Check that required database configuration options are specified
required_keys = ['ENGINE', 'NAME']

for key in required_keys:
    if key not in db_config:  # pragma: no cover
        error_msg = f'Missing required database configuration value {key}'
        logger.error(error_msg)

        print('Error: ' + error_msg)
        sys.exit(-1)

"""
Special considerations for the database 'ENGINE' setting.
It can be specified in config.yaml (or envvar) as either (for example):
- sqlite3
- django.db.backends.sqlite3
- django.db.backends.postgresql
"""

db_engine = db_config['ENGINE'].lower()

# Correct common misspelling
if db_engine == 'sqlite':
    db_engine = 'sqlite3'  # pragma: no cover

if db_engine in ['sqlite3', 'postgresql', 'mysql']:
    # Prepend the required python module string
    db_engine = f'django.db.backends.{db_engine}'
    db_config['ENGINE'] = db_engine

db_name = db_config['NAME']
db_host = db_config.get('HOST', "''")

if 'sqlite' in db_engine:
    db_name = str(Path(db_name).resolve())
    db_config['NAME'] = db_name

logger.info(f"DB_ENGINE: {db_engine}")
logger.info(f"DB_NAME: {db_name}")
logger.info(f"DB_HOST: {db_host}")

"""
In addition to base-level database configuration, we may wish to specify specific options to the database backend
Ref: https://docs.djangoproject.com/en/3.2/ref/settings/#std:setting-OPTIONS
"""

# 'OPTIONS' or 'options' can be specified in config.yaml
# Set useful sensible timeouts for a transactional webserver to communicate
# with its database server, that is, if the webserver is having issues
# connecting to the database server (such as a replica failover) don't sit and
# wait for possibly an hour or more, just tell the client something went wrong
# and let the client retry when they want to.
db_options = db_config.get("OPTIONS", db_config.get("options", {}))

# Specific options for postgres backend
if "postgres" in db_engine:  # pragma: no cover
    from psycopg2.extensions import (ISOLATION_LEVEL_READ_COMMITTED,
                                     ISOLATION_LEVEL_SERIALIZABLE)

    # Connection timeout
    if "connect_timeout" not in db_options:
        # The DB server is in the same data center, it should not take very
        # long to connect to the database server
        # # seconds, 2 is minimum allowed by libpq
        db_options["connect_timeout"] = int(
            get_setting('INVENTREE_DB_TIMEOUT', 'database.timeout', 2)
        )

    # Setup TCP keepalive
    # DB server is in the same DC, it should not become unresponsive for
    # very long. With the defaults below we wait 5 seconds for the network
    # issue to resolve itself.  It it that doesn't happen whatever happened
    # is probably fatal and no amount of waiting is going to fix it.
    # # 0 - TCP Keepalives disabled; 1 - enabled
    if "keepalives" not in db_options:
        db_options["keepalives"] = int(
            get_setting('INVENTREE_DB_TCP_KEEPALIVES', 'database.tcp_keepalives', 1)
        )

    # Seconds after connection is idle to send keep alive
    if "keepalives_idle" not in db_options:
        db_options["keepalives_idle"] = int(
            get_setting('INVENTREE_DB_TCP_KEEPALIVES_IDLE', 'database.tcp_keepalives_idle', 1)
        )

    # Seconds after missing ACK to send another keep alive
    if "keepalives_interval" not in db_options:
        db_options["keepalives_interval"] = int(
            get_setting("INVENTREE_DB_TCP_KEEPALIVES_INTERVAL", "database.tcp_keepalives_internal", "1")
        )

    # Number of missing ACKs before we close the connection
    if "keepalives_count" not in db_options:
        db_options["keepalives_count"] = int(
            get_setting("INVENTREE_DB_TCP_KEEPALIVES_COUNT", "database.tcp_keepalives_count", "5")
        )

    # # Milliseconds for how long pending data should remain unacked
    # by the remote server
    # TODO: Supported starting in PSQL 11
    # "tcp_user_timeout": int(os.getenv("PGTCP_USER_TIMEOUT", "1000"),

    # Postgres's default isolation level is Read Committed which is
    # normally fine, but most developers think the database server is
    # actually going to do Serializable type checks on the queries to
    # protect against simultaneous changes.
    # https://www.postgresql.org/docs/devel/transaction-iso.html
    # https://docs.djangoproject.com/en/3.2/ref/databases/#isolation-level
    if "isolation_level" not in db_options:
        serializable = get_boolean_setting('INVENTREE_DB_ISOLATION_SERIALIZABLE', 'database.serializable', False)
        db_options["isolation_level"] = ISOLATION_LEVEL_SERIALIZABLE if serializable else ISOLATION_LEVEL_READ_COMMITTED

# Specific options for MySql / MariaDB backend
elif "mysql" in db_engine:  # pragma: no cover
    # TODO TCP time outs and keepalives

    # MariaDB's default isolation level is Repeatable Read which is
    # normally fine, but most developers think the database server is
    # actually going to Serializable type checks on the queries to
    # protect against siumltaneous changes.
    # https://mariadb.com/kb/en/mariadb-transactions-and-isolation-levels-for-sql-server-users/#changing-the-isolation-level
    # https://docs.djangoproject.com/en/3.2/ref/databases/#mysql-isolation-level
    if "isolation_level" not in db_options:
        serializable = get_boolean_setting('INVENTREE_DB_ISOLATION_SERIALIZABLE', 'database.serializable', False)
        db_options["isolation_level"] = "serializable" if serializable else "read committed"

# Specific options for sqlite backend
elif "sqlite" in db_engine:
    # TODO: Verify timeouts are not an issue because no network is involved for SQLite

    # SQLite's default isolation level is Serializable due to SQLite's
    # single writer implementation.  Presumably as a result of this, it is
    # not possible to implement any lower isolation levels in SQLite.
    # https://www.sqlite.org/isolation.html
    pass

# Provide OPTIONS dict back to the database configuration dict
db_config['OPTIONS'] = db_options

# Set testing options for the database
db_config['TEST'] = {
    'CHARSET': 'utf8',
}

# Set collation option for mysql test database
if 'mysql' in db_engine:
    db_config['TEST']['COLLATION'] = 'utf8_general_ci'  # pragma: no cover

DATABASES = {
    'default': db_config
}

# login settings
REMOTE_LOGIN = get_boolean_setting('INVENTREE_REMOTE_LOGIN', 'remote_login_enabled', False)
REMOTE_LOGIN_HEADER = get_setting('INVENTREE_REMOTE_LOGIN_HEADER', 'remote_login_header', 'REMOTE_USER')

# Magic login django-sesame
SESAME_MAX_AGE = 300
# LOGIN_REDIRECT_URL = "/platform/logged-in/"
LOGIN_REDIRECT_URL = "/index/"

# sentry.io integration for error reporting
SENTRY_ENABLED = get_boolean_setting('INVENTREE_SENTRY_ENABLED', 'sentry_enabled', False)

# Default Sentry DSN (can be overridden if user wants custom sentry integration)
SENTRY_DSN = get_setting('INVENTREE_SENTRY_DSN', 'sentry_dsn', default_sentry_dsn())
SENTRY_SAMPLE_RATE = float(get_setting('INVENTREE_SENTRY_SAMPLE_RATE', 'sentry_sample_rate', 0.1))

if SENTRY_ENABLED and SENTRY_DSN:  # pragma: no cover

    inventree_tags = {
        'testing': TESTING,
        'docker': DOCKER,
        'debug': DEBUG,
        'remote': REMOTE_LOGIN,
    }

    init_sentry(SENTRY_DSN, SENTRY_SAMPLE_RATE, inventree_tags)

# Cache configuration
cache_host = get_setting('INVENTREE_CACHE_HOST', 'cache.host', None)
cache_port = get_setting('INVENTREE_CACHE_PORT', 'cache.port', '6379', typecast=int)

if cache_host:  # pragma: no cover
    # We are going to rely upon a possibly non-localhost for our cache,
    # so don't wait too long for the cache as nothing in the cache should be
    # irreplaceable.
    _cache_options = {
        "CLIENT_CLASS": "django_redis.client.DefaultClient",
        "SOCKET_CONNECT_TIMEOUT": int(os.getenv("CACHE_CONNECT_TIMEOUT", "2")),
        "SOCKET_TIMEOUT": int(os.getenv("CACHE_SOCKET_TIMEOUT", "2")),
        "CONNECTION_POOL_KWARGS": {
            "socket_keepalive": config.is_true(
                os.getenv("CACHE_TCP_KEEPALIVE", "1")
            ),
            "socket_keepalive_options": {
                socket.TCP_KEEPCNT: int(
                    os.getenv("CACHE_KEEPALIVES_COUNT", "5")
                ),
                socket.TCP_KEEPIDLE: int(
                    os.getenv("CACHE_KEEPALIVES_IDLE", "1")
                ),
                socket.TCP_KEEPINTVL: int(
                    os.getenv("CACHE_KEEPALIVES_INTERVAL", "1")
                ),
                socket.TCP_USER_TIMEOUT: int(
                    os.getenv("CACHE_TCP_USER_TIMEOUT", "1000")
                ),
            },
        },
    }
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f"redis://{cache_host}:{cache_port}/0",
            "OPTIONS": _cache_options,
        },
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
    }

_q_worker_timeout = int(get_setting('INVENTREE_BACKGROUND_TIMEOUT', 'background.timeout', 90))

# django-q background worker configuration
Q_CLUSTER = {
    'name': 'InvenTree',
    'label': 'Background Tasks',
    'workers': int(get_setting('INVENTREE_BACKGROUND_WORKERS', 'background.workers', 4)),
    'timeout': _q_worker_timeout,
    'retry': min(120, _q_worker_timeout + 30),
    'max_attempts': int(get_setting('INVENTREE_BACKGROUND_MAX_ATTEMPTS', 'background.max_attempts', 5)),
    'queue_limit': 50,
    'catch_up': False,
    'bulk': 10,
    'orm': 'default',
    'cache': 'default',
    'sync': False,
}

# Configure django-q sentry integration
if SENTRY_ENABLED and SENTRY_DSN:
    Q_CLUSTER['error_reporter'] = {
        'sentry': {
            'dsn': SENTRY_DSN
        }
    }

if cache_host:  # pragma: no cover
    # If using external redis cache, make the cache the broker for Django Q
    # as well
    Q_CLUSTER["django_redis"] = "worker"

# database user sessions
SESSION_ENGINE = 'user_sessions.backends.db'
LOGOUT_REDIRECT_URL = get_setting('INVENTREE_LOGOUT_REDIRECT_URL', 'logout_redirect_url', 'index')
SILENCED_SYSTEM_CHECKS = [
    'admin.E410',
]

# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Extra (optional) URL validators
# See https://docs.djangoproject.com/en/2.2/ref/validators/#django.core.validators.URLValidator

EXTRA_URL_SCHEMES = get_setting('INVENTREE_EXTRA_URL_SCHEMES', 'extra_url_schemes', [])

if type(EXTRA_URL_SCHEMES) not in [list]:  # pragma: no cover
    logger.warning("extra_url_schemes not correctly formatted")
    EXTRA_URL_SCHEMES = []

# Internationalization
# https://docs.djangoproject.com/en/dev/topics/i18n/
LANGUAGE_CODE = get_setting('INVENTREE_LANGUAGE', 'language', 'en-us')
# Store language settings for 30 days
LANGUAGE_COOKIE_AGE = 2592000

# If a new language translation is supported, it must be added here
# After adding a new language, run the following command:
# python manage.py makemessages -l <language_code> -e html,js,py --nowrap
LANGUAGES = [
    ('cs', _('Czech')),
    ('da', _('Danish')),
    ('de', _('German')),
    ('el', _('Greek')),
    ('en', _('English')),
    ('es', _('Spanish')),
    ('es-mx', _('Spanish (Mexican)')),
    ('fa', _('Farsi / Persian')),
    ('fi', _('Finnish')),
    ('fr', _('French')),
    ('he', _('Hebrew')),
    ('hi', _('Hindi')),
    ('hu', _('Hungarian')),
    ('it', _('Italian')),
    ('ja', _('Japanese')),
    ('ko', _('Korean')),
    ('nl', _('Dutch')),
    ('no', _('Norwegian')),
    ('pl', _('Polish')),
    ('pt', _('Portuguese')),
    ('pt-br', _('Portuguese (Brazilian)')),
    ('ru', _('Russian')),
    ('sl', _('Slovenian')),
    ('sv', _('Swedish')),
    ('th', _('Thai')),
    ('tr', _('Turkish')),
    ('vi', _('Vietnamese')),
    ('zh-hans', _('Chinese (Simplified)')),
    ('zh-hant', _('Chinese (Traditional)')),
]

# Testing interface translations
if get_boolean_setting('TEST_TRANSLATIONS', default_value=False):  # pragma: no cover
    # Set default language
    LANGUAGE_CODE = 'xx'

    # Add to language catalog
    LANGUAGES.append(('xx', 'Test'))

    # Add custom languages not provided by Django
    EXTRA_LANG_INFO = {
        'xx': {
            'code': 'xx',
            'name': 'Test',
            'name_local': 'Test'
        },
    }
    LANG_INFO = dict(django.conf.locale.LANG_INFO, **EXTRA_LANG_INFO)
    django.conf.locale.LANG_INFO = LANG_INFO

# Currencies available for use
CURRENCIES = get_setting(
    'INVENTREE_CURRENCIES', 'currencies',
    ['AUD', 'CAD', 'CNY', 'EUR', 'GBP', 'JPY', 'NZD', 'USD'],
    typecast=list,
)

# Ensure that at least one currency value is available
if len(CURRENCIES) == 0:  # pragma: no cover
    logger.warning("No currencies selected: Defaulting to USD")
    CURRENCIES = ['USD']

# Maximum number of decimal places for currency rendering
CURRENCY_DECIMAL_PLACES = 6

# Check that each provided currency is supported
for currency in CURRENCIES:
    if currency not in moneyed.CURRENCIES:  # pragma: no cover
        logger.error(f"Currency code '{currency}' is not supported")
        sys.exit(1)

# Custom currency exchange backend
EXCHANGE_BACKEND = 'InvenTree.exchange.InvenTreeExchange'

# Email configuration options
EMAIL_BACKEND = get_setting('INVENTREE_EMAIL_BACKEND', 'email.backend', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = get_setting('INVENTREE_EMAIL_HOST', 'email.host', '')
EMAIL_PORT = get_setting('INVENTREE_EMAIL_PORT', 'email.port', 25, typecast=int)
EMAIL_HOST_USER = get_setting('INVENTREE_EMAIL_USERNAME', 'email.username', '')
EMAIL_HOST_PASSWORD = get_setting('INVENTREE_EMAIL_PASSWORD', 'email.password', '')
EMAIL_SUBJECT_PREFIX = get_setting('INVENTREE_EMAIL_PREFIX', 'email.prefix', '[InvenTree] ')
EMAIL_USE_TLS = get_boolean_setting('INVENTREE_EMAIL_TLS', 'email.tls', False)
EMAIL_USE_SSL = get_boolean_setting('INVENTREE_EMAIL_SSL', 'email.ssl', False)

DEFAULT_FROM_EMAIL = get_setting('INVENTREE_EMAIL_SENDER', 'email.sender', '')

# If "from" email not specified, default to the username
if not DEFAULT_FROM_EMAIL:
    DEFAULT_FROM_EMAIL = get_setting('INVENTREE_EMAIL_USERNAME', 'email.username', '')

EMAIL_USE_LOCALTIME = False
EMAIL_TIMEOUT = 60

LOCALE_PATHS = (
    BASE_DIR.joinpath('locale/'),
)

TIME_ZONE = get_setting('INVENTREE_TIMEZONE', 'timezone', 'UTC')

USE_I18N = True

USE_L10N = True

# Do not use native timezone support in "test" mode
# It generates a *lot* of cruft in the logs
if not TESTING:
    USE_TZ = True  # pragma: no cover

DATE_INPUT_FORMATS = [
    "%Y-%m-%d",
]

# crispy forms use the bootstrap templates
CRISPY_TEMPLATE_PACK = 'bootstrap4'

# Use database transactions when importing / exporting data
IMPORT_EXPORT_USE_TRANSACTIONS = True

SITE_ID = 1

# Load the allauth social backends
SOCIAL_BACKENDS = get_setting('INVENTREE_SOCIAL_BACKENDS', 'social_backends', [], typecast=list)

for app in SOCIAL_BACKENDS:
    INSTALLED_APPS.append(app)  # pragma: no cover

SOCIALACCOUNT_PROVIDERS = get_setting('INVENTREE_SOCIAL_PROVIDERS', 'social_providers', None, typecast=dict)

SOCIALACCOUNT_STORE_TOKENS = True

# settings for allauth
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = get_setting('INVENTREE_LOGIN_CONFIRM_DAYS', 'login_confirm_days', 3, typecast=int)
ACCOUNT_LOGIN_ATTEMPTS_LIMIT = get_setting('INVENTREE_LOGIN_ATTEMPTS', 'login_attempts', 5, typecast=int)
ACCOUNT_DEFAULT_HTTP_PROTOCOL = get_setting('INVENTREE_LOGIN_DEFAULT_HTTP_PROTOCOL', 'login_default_protocol', 'http')
ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE = True
ACCOUNT_PREVENT_ENUMERATION = True
# 2FA
REMOVE_SUCCESS_URL = 'settings'

# override forms / adapters
ACCOUNT_FORMS = {
    'login': 'allauth.account.forms.LoginForm',
    'signup': 'InvenTree.forms.CustomSignupForm',
    'add_email': 'allauth.account.forms.AddEmailForm',
    'change_password': 'allauth.account.forms.ChangePasswordForm',
    'set_password': 'allauth.account.forms.SetPasswordForm',
    'reset_password': 'allauth.account.forms.ResetPasswordForm',
    'reset_password_from_key': 'allauth.account.forms.ResetPasswordKeyForm',
    'disconnect': 'allauth.socialaccount.forms.DisconnectForm',
}

SOCIALACCOUNT_ADAPTER = 'InvenTree.forms.CustomSocialAccountAdapter'
ACCOUNT_ADAPTER = 'InvenTree.forms.CustomAccountAdapter'

# Markdownify configuration
# Ref: https://django-markdownify.readthedocs.io/en/latest/settings.html

MARKDOWNIFY = {
    'default': {
        'BLEACH': True,
        'WHITELIST_ATTRS': [
            'href',
            'src',
            'alt',
        ],
        'MARKDOWN_EXTENSIONS': [
            'markdown.extensions.extra'
        ],
        'WHITELIST_TAGS': [
            'a',
            'abbr',
            'b',
            'blockquote',
            'em',
            'h1', 'h2', 'h3',
            'i',
            'img',
            'li',
            'ol',
            'p',
            'strong',
            'ul',
            'table',
            'thead',
            'tbody',
            'th',
            'tr',
            'td'
        ],
    }
}

# Ignore these error typeps for in-database error logging
IGNORED_ERRORS = [
    Http404,
    django.core.exceptions.PermissionDenied,
]

# Maintenance mode
MAINTENANCE_MODE_RETRY_AFTER = 60
MAINTENANCE_MODE_STATE_BACKEND = 'maintenance_mode.backends.StaticStorageBackend'

# Are plugins enabled?
PLUGINS_ENABLED = get_boolean_setting('INVENTREE_PLUGINS_ENABLED', 'plugins_enabled', False)

PLUGIN_FILE = config.get_plugin_file()

# Plugin test settings
PLUGIN_TESTING = get_setting('INVENTREE_PLUGIN_TESTING', 'PLUGIN_TESTING', TESTING)                     # Are plugins being tested?
PLUGIN_TESTING_SETUP = get_setting('INVENTREE_PLUGIN_TESTING_SETUP', 'PLUGIN_TESTING_SETUP', False)     # Load plugins from setup hooks in testing?
PLUGIN_TESTING_EVENTS = False                                                                           # Flag if events are tested right now
PLUGIN_RETRY = get_setting('INVENTREE_PLUGIN_RETRY', 'PLUGIN_RETRY', 5)                                 # How often should plugin loading be tried?
PLUGIN_FILE_CHECKED = False                                                                             # Was the plugin file checked?

# Site URL can be specified statically, or via a run-time setting
SITE_URL = get_setting('INVENTREE_SITE_URL', 'site_url', None)

if SITE_URL:
    logger.info(f"Site URL: {SITE_URL}")

    # Check that the site URL is valid
    validator = URLValidator()
    validator(SITE_URL)

# User interface customization values
CUSTOM_LOGO = get_custom_file('INVENTREE_CUSTOM_LOGO', 'customize.logo', 'custom logo', lookup_media=True)
CUSTOM_SPLASH = get_custom_file('INVENTREE_CUSTOM_SPLASH', 'customize.splash', 'custom splash')

CUSTOMIZE = get_setting('INVENTREE_CUSTOMIZE', 'customize', {})
if DEBUG:
    logger.info("InvenTree running with DEBUG enabled")

logger.info(f"MEDIA_ROOT: '{MEDIA_ROOT}'")
logger.info(f"STATIC_ROOT: '{STATIC_ROOT}'")

# Flags
FLAGS = {
    'EXPERIMENTAL': [
        {'condition': 'boolean', 'value': DEBUG},
        {'condition': 'parameter', 'value': 'experimental='},
    ],  # Should experimental features be turned on?
    'NEXT_GEN': [
        {'condition': 'parameter', 'value': 'ngen='},
    ],  # Should next-gen features be turned on?
}

# Get custom flags from environment/yaml
CUSTOM_FLAGS = get_setting('INVENTREE_FLAGS', 'flags', None, typecast=dict)
if CUSTOM_FLAGS:
    if not isinstance(CUSTOM_FLAGS, dict):
        logger.error(f"Invalid custom flags, must be valid dict: {CUSTOM_FLAGS}")
    else:
        logger.info(f"Custom flags: {CUSTOM_FLAGS}")
        FLAGS.update(CUSTOM_FLAGS)
