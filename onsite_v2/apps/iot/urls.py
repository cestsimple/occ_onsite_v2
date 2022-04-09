from django.conf.urls import url
from . import views

urlpatterns = [
    # 获取IOT数据
    url(r'^iot/site/$', views.SiteData.as_view()),
    url(r'^iot/asset/$', views.AssetData.as_view()),
    url(r'^iot/tag/$', views.TagData.as_view()),
    url(r'^iot/variable/$', views.VariableData.as_view()),
]
