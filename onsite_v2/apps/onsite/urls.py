from django.conf.urls import url
from . import views

urlpatterns = [
    # 计算
    url(r'^filling/calculate/$', views.FillingCalculate.as_view()),
    url(r'^filling/monthly/calculate/$', views.FillMonthlyCalculate.as_view()),
    url(r'^daily/calculate/$', views.DailyCalculate.as_view()),
    url(r'^monthly/invoice/calculate/$', views.InvoiceDiffCalculate.as_view()),

    # filling
    url(r'^filling/$', views.FillingModelView.as_view({'get': 'list', 'post': 'create'})),
    url(r'^filling/(?P<pk>\d+)/$',
        views.FillingModelView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})),

    # filling 月报
    url(r'^monthly/filling/$', views.FillMonthlyView.as_view({'get': 'list'})),
    url(r'^monthly/filling/(?P<pk>\d+)/$', views.FillMonthlyView.as_view({'put': 'update'})),

    # daily
    url(r'^daily/$', views.DailyModelView.as_view({'get': 'list'})),
    url(r'^daily/(?P<pk>\d+)/$', views.DailyModelView.as_view({'put': 'update'})),
    # daily_mod
    url(r'^daily/mod/(?P<pk>\d+)/$', views.DailyModModelView.as_view({'get': 'retrieve', 'put': 'update'})),
    # daily_origin
    url(r'^daily/origin/(?P<pk>\d+)/$', views.DailyOriginView.as_view()),

    # malfunction
    url(r'^malfunction/$', views.MalfunctionModelView.as_view({'get': 'list', 'post': 'create'})),
    url(r'^malfunction/(?P<pk>\d+)/$',
        views.MalfunctionModelView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})),

    # reason
    url(r'^malfunction/reason/$', views.ReasonModelView.as_view({'get': 'list'})),
    # reason-detail
    url(r'^malfunction/reason/detail/$', views.ReasonDetailModelView.as_view({'get': 'list'})),

    # monthly variable
    url(r'^monthly/variable/$', views.MonthlyVariableModelView.as_view({'get': 'list', 'post': 'create'})),
    url(r'^monthly/variable/(?P<pk>\d+)/$',
            views.MonthlyVariableModelView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})),

    # invoice variable diff
    url(r'^monthly/variable/diff/$', views.InvoiceDiffModelView.as_view({'get': 'list'})),
    url(r'^monthly/variable/diff/(?P<pk>\d+)/$',
            views.InvoiceDiffModelView.as_view({'get': 'retrieve', 'put': 'update'})),
]
