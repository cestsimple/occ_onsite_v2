from django.conf.urls import url
from rest_framework_jwt.views import obtain_jwt_token

from . import views

urlpatterns = [
    # JWT登录验证
    url(r'^user/auth/$', obtain_jwt_token),

    # 获取用户数据
    url(r'^user/$', views.UserView.as_view({'get': 'list', 'post': 'create'})),
    url(r'^user/(?P<pk>\d+)/$', views.UserView.as_view({'get': 'retrieve', 'put': 'update'})),
]