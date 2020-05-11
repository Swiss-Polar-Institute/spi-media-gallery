"""
Django settings for SpiMediaGallery project.

Generated by 'django-admin startproject' using Django 2.2.2.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import json
import os
import pathlib
from collections import namedtuple

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!

# Note: If in production change this in the local_settings.py
SECRET_KEY = 'w0!0umbw+uq$#e943ezmvny1!jo-*72q%#ds+v1=g2rz)#aamj'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'leaflet',
    'main',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'SpiMediaGallery.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'SpiMediaGallery.wsgi.application'


def secrets_file(file_name):
    """ First try $HOME/.file_name, else tries /run/secrets/file_name, else raises an exception"""
    file_path_in_home_directory = os.path.join(str(pathlib.Path.home()), "." + file_name)
    if os.path.exists(file_path_in_home_directory):
        return file_path_in_home_directory

    file_path_in_run_secrets = os.path.join("/run/secrets", file_name)
    if os.path.exists(file_path_in_run_secrets):
        return file_path_in_run_secrets

    raise FileNotFoundError("Configuration for {} doesn't exist".format(file_name))


def find_file(file_name):
    """ First try $HOME/file_name, then /code/file_name, else raises an exception"""
    file_path_in_home_directory = os.path.join(str(pathlib.Path.home()), file_name)
    if os.path.exists(file_path_in_home_directory):
        return file_path_in_home_directory

    file_path_in_code = os.path.join("/code", file_name)
    if os.path.exists(file_path_in_code):
        return file_path_in_code

    return None


if os.getenv('FORCE_SQLITE3_DATABASE', False):
    SPATIALITE_LIBRARY_PATH = 'mod_spatialite.so'

    DATABASES = {
        'default': {
            'ENGINE': 'django.contrib.gis.db.backends.spatialite',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.contrib.gis.db.backends.mysql',
            'OPTIONS': {
                'read_default_file': secrets_file("spi_media_gallery_mysql.conf"),
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                'charset': 'utf8mb4',
            },
            'TEST': {
                'NAME': 'test_spi_media_gallery',
            }
        }
    }

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

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

CACHE_ENABLED = True

if CACHE_ENABLED:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
            'LOCATION': '/tmp/django_cache',
            'TIMEOUT': 300,
            'OPTIONS': {
                'MAX_ENTRIES': 1000
            }
        }
    }
    # To enable caching in all the website
    # MIDDLEWARE.insert(0, 'django.middleware.cache.UpdateCacheMiddleware')
    # MIDDLEWARE.append('django.middleware.cache.FetchFromCacheMiddleware')

# It's in this place for convenience in the staging environment
with open(secrets_file("spi_media_gallery_buckets.json")) as json_file:
    BUCKETS_CONFIGURATION = json.load(json_file)
    """
    Example file:

    {
    "photos": {
        "name": "photos",
        "endpoint": "http://localhost:9000",
        "access_key": "minio",
        "secret_key": "minio123"
    },
    "processed": {
        "name": "processed",
        "endpoint": "http://localhost:9000",
        "access_key": "minio",
        "secret_key": "minio123"
    }
}
    """

RESIZED_PREFIX = "media-gallery/resized"

IMAGE_LABEL_TO_SIZES = {
    'T': (415, 415),
    'S': (640, 640),
    'M': (1280, 1280),
    'L': (1920, 1920)
}

Format = namedtuple('Format', ['content_type', 'dcraw_preprocessing'])

# Can add more from:
# Raw images: https://stackoverflow.com/questions/43473056/which-mime-type-should-be-used-for-a-raw-image
# Videos (and anything): https://www.sitepoint.com/mime-types-complete-list/

# ImageMagic needs to deal with the format (or via dcraw if dcraw_preprocessing is True)
PHOTO_FORMATS = {
    'arw': Format('image/x-sony-arw', True),
    'cr2': Format('image/x-canon-cr2', True),
    'jpeg': Format('image/jpeg', False),
    'jpg': Format('image/jpeg', False),
    'nef': Format('image/x-nikon-nef', True),
}

# ffmpeg needs to deal with the format
VIDEO_FORMATS = {
    'avi': Format('video/avi', False),
    'mov': Format('video/quicktime', False),
    'mp4': Format('video/mp4', False),
    'mpeg': Format('video/mpeg', False),
    'mpg': Format('video/mpeg', False),
    'webm': Format('video/webm', False)
}

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

TRACK_MAP_FILEPATH = '/tmp/test.geojson'

DATETIME_POSITIONS_SQLITE3_PATH = find_file("gps.sqlite3")

PROXY_TO_OBJECT_STORAGE = False

SITE_ADMINISTRATOR = "Carles Pina"

try:
    from local_settings import *
except ImportError:
    pass
