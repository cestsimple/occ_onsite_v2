from django.conf.urls import url
from . import views

urlpatterns = [
    # 获取IOT所有Site数据
    url(r'^iot/site/$', views.SiteData.as_view()),

    # 获取IOT所有Asset数据
    url(r'^iot/asset/$', views.AssetData.as_view()),

    # 获取IOT所有Tag数据
    url(r'^iot/tag/$', views.TagData.as_view()),
]
