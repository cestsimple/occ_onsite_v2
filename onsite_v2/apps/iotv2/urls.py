from django.conf.urls import url

from . import views

urlpatterns = [
    # 获取IOT数据
    url(r'^asset/refresh/$', views.AssetRefresh.as_view()),

    # Apsa列表
    url(r'^apsas/$', views.apsa_list),
]
