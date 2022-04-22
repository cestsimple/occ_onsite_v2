from django.conf.urls import url
from . import views

urlpatterns = [
    # 计算
    url(r'^api/filling/calculate/$', views.FillingCalculate.as_view()),
    url(r'^api/daily/calculate/$', views.DailyCalculate.as_view()),

    # 增删改查
    # filling
    url(r'^api/filling/$', views.FillingModelView.as_view({'get': 'list', 'post': 'create'})),
    url(r'^api/filling/(?P<pk>\d+)/$',
        views.FillingModelView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})),

    # daily
    url(r'^api/daily/$', views.DailyModelView.as_view({'get': 'list'})),
    # daily_mod
    url(r'^api/daily/mod/(?P<pk>\d+)/$', views.DailyModModelView.as_view({'get': 'retrieve', 'put': 'update'})),
    # daily_origin
    url(r'^api/daily/origin/(?P<pk>\d+)/$', views.DailyOriginView.as_view()),

    # malfunction
    url(r'^api/malfunction/$', views.MalfunctionModelView.as_view({'get': 'list', 'post': 'create'})),
    url(r'^api/malfunction/(?P<pk>\d+)/$',
        views.MalfunctionModelView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})),

    # reason
    url(r'^api/malfunction/reason/$', views.ReasonModelView.as_view({'get': 'list'})),
]
