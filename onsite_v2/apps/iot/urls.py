from django.conf.urls import url
from . import views

urlpatterns = [
    # 获取IOT数据
    url(r'^iot/site/$', views.SiteData.as_view()),
    url(r'^iot/asset/$', views.AssetData.as_view()),
    url(r'^iot/tag/$', views.TagData.as_view()),
    url(r'^iot/variable/$', views.VariableData.as_view()),

    # 查询site修改数据
    url(r'^site/page/$', views.SitePage.as_view()),
    url(r'^site/$', views.SiteModelView.as_view({'get': 'list'})),
    url(r'^site/(?P<pk>\d+)/$', views.SiteModelView.as_view({'get': 'retrieve', 'put': 'update'})),

    # 查询apsa修改数据
    url(r'^apsa/page/$', views.ApsaPage.as_view()),
    url(r'^apsa/$', views.ApsaModelView.as_view({'get': 'list'})),
    url(r'^apsa/(?P<pk>\d+)/$', views.ApsaModelView.as_view({'get': 'retrieve', 'put': 'update'})),

    # 查询bulk修改数据
    url(r'^bulk/page/$', views.BulkPage.as_view()),
    url(r'^bulk/$', views.BulkModelView.as_view({'get': 'list'})),
    url(r'^bulk/(?P<pk>\d+)/$', views.BulkModelView.as_view({'get': 'retrieve', 'put': 'update'})),

    # 查询asset修改数据
    url(r'^asset/$', views.AssetModelView.as_view({'get': 'list'})),
    url(r'^asset/(?P<pk>\d+)/$', views.AssetModelView.as_view({'get': 'retrieve', 'put': 'update'})),

    # 查询engineer修改数据
    url(r'^engineer/$', views.EngineerModelView.as_view({'get': 'list'})),
    url(r'^engineer/(?P<pk>\d+)/$', views.EngineerModelView.as_view({'get': 'retrieve', 'put': 'update'})),
]
