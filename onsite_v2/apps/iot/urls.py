from django.conf.urls import url
from . import views

urlpatterns = [
    # 获取IOT数据
    url(r'^api/iot/site/$', views.SiteData.as_view()),
    url(r'^api/iot/asset/$', views.AssetData.as_view()),
    url(r'^api/iot/tag/$', views.TagData.as_view()),
    url(r'^api/iot/variable/$', views.VariableData.as_view()),
    url(r'^api/iot/record/$', views.RecordData.as_view()),

    # 查询site修改数据
    url(r'^api/site/$', views.SiteModelView.as_view({'get': 'list'})),
    url(r'^api/site/(?P<pk>\d+)/$', views.SiteModelView.as_view({'get': 'retrieve', 'put': 'update'})),

    # 查询apsa修改数据
    url(r'^api/apsa/$', views.ApsaModelView.as_view({'get': 'list'})),
    url(r'^api/apsa/(?P<pk>\d+)/$', views.ApsaModelView.as_view({'get': 'retrieve', 'put': 'update'})),

    # 查询bulk修改数据
    url(r'^api/bulk/$', views.BulkModelView.as_view({'get': 'list'})),
    url(r'^api/bulk/(?P<pk>\d+)/$', views.BulkModelView.as_view({'get': 'retrieve', 'put': 'update'})),

    # 查询bulk修改数据
    url(r'^api/variable/$', views.VariableModelView.as_view({'get': 'list'})),
    url(r'^api/variable/(?P<pk>\d+)/$', views.VariableModelView.as_view({'get': 'retrieve', 'put': 'update'})),

    # 查询asset修改数据
    url(r'^api/asset/$', views.AssetModelView.as_view({'get': 'list', 'put': 'update'})),
    url(r'^api/asset/(?P<pk>\d+)/$', views.AssetModelView.as_view({'get': 'retrieve', 'put': 'update'})),
]
