from django.conf.urls import url
from . import views

urlpatterns = [
    # 计算
    url(r'^filling/calculate/$', views.FillingCalculate.as_view()),
    url(r'^daily/calculate/$', views.DailyCalculate.as_view()),

    # 增删改查
    # filling
    url(r'^filling/$', views.FillingModelView.as_view({'get': 'list', 'put': 'update'})),
    url(r'^filling/(?P<pk>\d+)/$', views.FillingModelView.as_view({'get': 'retrieve', 'put': 'update'})),
    # daily
    url(r'^daily/$', views.DailyModelView.as_view({'get': 'list'})),
    # daily_mod
    url(r'^daily/mod/(?P<pk>\d+)/$', views.DailyModModelView.as_view({'get': 'retrieve', 'put': 'update'})),
]