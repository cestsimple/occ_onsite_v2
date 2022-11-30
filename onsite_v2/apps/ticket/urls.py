# -*- coding:utf-8 -*-
from django.conf.urls import url

from apps.ticket import views

urlpatterns = [
    # project
    url(r'^ticket/projects/$', views.ProjectView.as_view({'get': 'list', 'post': 'create'})),
    url(r'^ticket/project/(?P<pk>\d+)/$',
        views.ProjectView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})),

    # node
    url(r'^ticket/nodes/$', views.NodeView.as_view({'get': 'list', 'post': 'create'})),
    url(r'^ticket/node/(?P<pk>\d+)/$',
        views.NodeView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})),

    # node content
    url(r'^ticket/node/contents/$', views.NodeContentView.as_view({'get': 'list', 'post': 'create'})),
    url(r'^ticket/node/content/(?P<pk>\d+)/$',
        views.NodeContentView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})),
]
