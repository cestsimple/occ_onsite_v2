from django.conf.urls import url
from rest_framework_jwt.views import obtain_jwt_token

from . import views

urlpatterns = [
    # JWT登录验证
    url(r'^ticket/ping/$', views.PingView.as_view()),
]
