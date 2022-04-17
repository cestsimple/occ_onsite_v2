from django.conf.urls import url
from . import views

urlpatterns = [
    # 获取IOT数据
    url(r'^iot/site/$', views.SiteData.as_view()),
    url(r'^iot/asset/$', views.AssetData.as_view()),
    url(r'^iot/tag/$', views.TagData.as_view()),
    url(r'^iot/variable/$', views.VariableData.as_view()),
    url(r'^iot/record/$', views.RecordData.as_view()),

    # 查询site修改数据
    url(r'^site/$', views.SiteModelView.as_view({'get': 'list'})),
    url(r'^site/(?P<pk>\d+)/$', views.SiteModelView.as_view({'get': 'retrieve', 'put': 'update'})),
    url(r'^site/search/$', views.SiteModelView.as_view({'get': 'search'})),

    # 查询apsa修改数据
    url(r'^apsa/$', views.ApsaModelView.as_view({'get': 'list'})),
    url(r'^apsa/(?P<pk>\d+)/$', views.ApsaModelView.as_view({'get': 'retrieve', 'put': 'update'})),

    # 查询bulk修改数据
    url(r'^bulk/$', views.BulkModelView.as_view({'get': 'list'})),
    url(r'^bulk/(?P<pk>\d+)/$', views.BulkModelView.as_view({'get': 'retrieve', 'put': 'update'})),

    # 查询bulk修改数据
    url(r'^variable/$', views.VariableModelView.as_view({'get': 'list'})),
    url(r'^variable/(?P<pk>\d+)/$', views.VariableModelView.as_view({'get': 'retrieve', 'put': 'update'})),
    url(r'^variable/search/$', views.VariableModelView.as_view({'get': 'search'})),

    # 查询asset修改数据
    # url(r'^asset/$', views.AssetModelView.as_view({'get': 'list'})),
    # url(r'^asset/(?P<pk>\d+)/$', views.AssetModelView.as_view({'get': 'retrieve', 'put': 'update'})),
]
