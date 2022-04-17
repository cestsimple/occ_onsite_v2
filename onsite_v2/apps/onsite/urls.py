from django.conf.urls import url
from . import views

urlpatterns = [
    # 主页
    url(r'^home/$', views.IndexView.as_view(), name='index'),

    # url(r'^user/$', views.UserView.as_view({'get': 'list', 'post': 'create'})),
    # url(r'^user/(?P<pk>\d+)/$', views.UserView.as_view({'get': 'retrieve', 'put': 'update'})),
    # url(r'^user/search/$', views.UserView.as_view({'get': 'search'})),
]