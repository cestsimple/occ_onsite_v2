from django.conf.urls import url
from . import views

urlpatterns = [
    # 计算
    url(r'^filling/calculate/$', views.FillingCalculate.as_view()),
    url(r'^daily/calculate/$', views.DailyCalculate.as_view()),

    # 增删改查
    # filling
    url(r'^filling/$', views.FillingModelView.as_view({'get': 'list', 'post': 'create'})),
    url(r'^filling/(?P<pk>\d+)/$',
        views.FillingModelView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})),

    # daily
    url(r'^daily/$', views.DailyModelView.as_view({'get': 'list'})),
    # daily_mod
    url(r'^daily/mod/(?P<pk>\d+)/$', views.DailyModModelView.as_view({'get': 'retrieve', 'put': 'update'})),

    # malfunction
    url(r'^malfunction/$', views.MalfunctionModelView.as_view({'get': 'list'})),
    url(r'^malfunction/(?P<pk>\d+)/$',
        views.MalfunctionModelView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})),

    # reason
    url(r'^malfunction/reason/$', views.ReasonModelView.as_view({'get': 'list'})),
]
