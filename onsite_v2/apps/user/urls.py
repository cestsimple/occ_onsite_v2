from django.conf.urls import url
from rest_framework_jwt.views import obtain_jwt_token

from . import views

urlpatterns = [
    # 主页
    url(r'^home/$', views.IndexView.as_view(), name='index'),

    # Admin用户创建
    url(r'^user/admin/$', views.AdminCreateView.as_view(), name='admin'),

    # 注册
    url(r'^user/login/$', views.LoginView.as_view(), name='login'),

    # JWT登录验证
    url(r'^user/auth/$', obtain_jwt_token),
]