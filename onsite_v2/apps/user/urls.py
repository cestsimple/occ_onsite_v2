from django.conf.urls import url
from rest_framework_jwt.views import obtain_jwt_token

from . import views

urlpatterns = [
    # JWT登录验证
    url(r'^user/auth/$', obtain_jwt_token),

    # 获取用户数据
    url(r'^user/$', views.UserView.as_view({'get': 'list', 'post': 'create'})),
    url(r'^user/(?P<pk>\d+)/$', views.UserView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})),

    # 角色管理
    url(r'^user/role/$', views.RoleModelView.as_view({'get': 'list', 'post': 'create'})),
    url(r'^user/role/(?P<pk>\d+)/$',
        views.RoleModelView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})),

    # 权限管理
    url(r'^user/permission/$', views.PermissionModelView.as_view({'get': 'list', 'post': 'create'})),
    url(r'^user/permission/(?P<pk>\d+)/$',
        views.PermissionModelView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})),

    # 角色权限管理
    url(r'^user/roleperm/$', views.RolePermissionModelView.as_view({'get': 'list', 'post': 'create'})),
    url(r'^user/roleperm/(?P<pk>\d+)/$',
        views.RolePermissionModelView.as_view({'get': 'retrieve', 'delete': 'destroy'})),

    # 用户角色管理
    url(r'^user/assignRole/$', views.UserAssignRole.as_view()),

    # 角色权限管理
    url(r'^user/role/assignPrem/$', views.RoleAssignPerm.as_view()),
]
