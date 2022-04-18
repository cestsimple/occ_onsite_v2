from django.conf.urls import url
from . import views

urlpatterns = [
    # 计算
    url(r'^filling/calculate/$', views.FillingCalculate.as_view()),
    url(r'^daily/calculate/$', views.DailyCalculate.as_view()),

    # url(r'^user/$', views.UserView.as_view({'get': 'list', 'post': 'create'})),
    # url(r'^user/(?P<pk>\d+)/$', views.UserView.as_view({'get': 'retrieve', 'put': 'update'})),
    # url(r'^user/search/$', views.UserView.as_view({'get': 'search'})),
]