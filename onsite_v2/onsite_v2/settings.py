import datetime
import os
import sys

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'nma(4vjm!(b&l5(q@)4b3es*b#u-=!7w*l&ma46cjy*3ws&7!_'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'apps.user',
    'apps.iot',
    'apps.onsite',
    'apps.ludan',
    'apps.ticket',
    'apps.request',
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'onsite_v2.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['frontend/dist'],
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
    # {
    #     # 配置Jinja2模板
    #     'BACKEND': 'django.template.backends.jinja2.Jinja2',
    #     # 新增模板文件夹
    #     'DIRS': [os.path.join(BASE_DIR, 'templates'), ],
    #     'APP_DIRS': True,
    #     'OPTIONS': {
    #         'context_processors': [
    #             'django.template.context_processors.debug',
    #             'django.template.context_processors.request',
    #             'django.contrib.auth.context_processors.auth',
    #             'django.contrib.messages.context_processors.messages',
    #         ],
    #         # 补充Jinja2模板规则环境
    #         'environment': 'utils.jinja2_env.jinja2_environment',
    #     },
    # },
]

WSGI_APPLICATION = 'onsite_v2.wsgi.application'

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    # 'default': {
    #     'ENGINE': 'sql_server.pyodbc',
    #     'NAME': 'IOT_V2',
    #     #'HOST': 'localhost',
    #     'HOST': 'localhost\SQLEXPRESS',
    #     'USER': 'django_iot',
    #     'PASSWORD': 'welcome',
    #     'PORT': '1433',
    #     'OPTIONS': {
    #         'query_timeout': 10,
    #         'driver': 'ODBC Driver 17 for SQL Server'
    #     }
    # }
    'default': {
        'ENGINE': 'django.db.backends.mysql',  # 数据库引擎
        # 'HOST': 'localhost', # 数据库主机
        'HOST': 'localhost',
        'PORT': 3306,  # 数据库端口
        'USER': 'django_iot',  # 数据库用户名
        'PASSWORD': 'welcome',  # 数据库用户密码
        'NAME': 'IOT_v2'  # 数据库名字
    },
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

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = True

# 修改后mysql时区统一
USE_TZ = False

# static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'
# 添加静态文件夹
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'frontend/dist'),
    os.path.join(BASE_DIR, 'frontend/dist/static'),
    os.path.join(BASE_DIR, 'static/'),
]

# 配置规则 '应用名.模型类名'
AUTH_USER_MODEL = 'user.User'

# 使用LoginMixin需要定义默认登录跳转URL
LOGIN_URL = '/user/login/'

# 配置时间格式，解决中间带T的问题
REST_FRAMEWORK = {
    'DATETIME_FORMAT': "%Y-%m-%d %H:%M",
    'EXCEPTION_HANDLER': 'utils.drf.exception_handler',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_jwt.authentication.JSONWebTokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ),
}
JWT_AUTH = {
    'JWT_EXPIRATION_DELTA': datetime.timedelta(days=7),
    'JWT_RESPONSE_PAYLOAD_HANDLER': 'utils.jwt_response.jwt_response_payload_handler',
}

# 跨域请求
CORS_ORIGIN_ALLOW_ALL = True

CORS_ALLOW_METHODS = ['*']

CORS_ALLOW_CREDENTIALS = True
