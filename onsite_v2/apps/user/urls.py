from django.conf.urls import url
from rest_framework_jwt.views import obtain_jwt_token

from . import views

urlpatterns = [
    # JWT登录验证
    url(r'^api/user/auth/$', obtain_jwt_token),

    # 获取用户数据
    url(r'^api/user/$', views.UserView.as_view({'get': 'list', 'post': 'create'})),
    url(r'^api/user/(?P<pk>\d+)/$', views.UserView.as_view({'get': 'retrieve', 'put': 'update'})),
]