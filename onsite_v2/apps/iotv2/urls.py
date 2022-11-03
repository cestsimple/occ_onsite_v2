from django.conf.urls import url

from . import views

urlpatterns = [
    # 获取IOT数据
    url(r'^asset/refresh/$', views.AssetRefresh.as_view()),

    # Apsa列表
    url(r'^apsas/$', views.ApsaV2View.as_view()),

    # Asset列表
    url(r'^assets/$', views.AssetV2View.as_view()),

    # 数据迁移
    url(r'^iot/migrate/$', views.migrate),
]
