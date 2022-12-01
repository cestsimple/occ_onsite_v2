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
    url(r'^ticket/node/content/$', views.NodeContentView.as_view({'post': 'create'})),
    url(r'^ticket/node/content/(?P<pk>\d+)/$',
        views.NodeContentView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})),

    # task
    url(r'^ticket/tasks/$', views.TaskView.as_view({'get': 'list', 'post': 'create'})),
    url(r'^ticket/task/(?P<pk>\d+)/$',
        views.TaskView.as_view({'get': 'retrieve', 'put': 'update'})),

    # task history
    url(r'^ticket/task/history/$', views.TaskHistoryView.as_view({'post': 'create'})),
    url(r'^ticket/task/history/(?P<pk>\d+)/$',
        views.TaskHistoryView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})),

    # custom api
    url(r'^ticket/task/mytodo/', views.get_my_todo_tasks)
]
