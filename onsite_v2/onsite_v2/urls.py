from django.conf.urls import url
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from ninja import NinjaAPI, Router

from apps.request.api import request_router

ninja_api = NinjaAPI(title="OCC ONLINE - API文档V3", version="dev", description="语言: Python\n框架: django-ninja",
                     docs_url='/api/docs')
# 创建路由节点
r = Router()
r.add_router('', request_router)

# api添加路由
ninja_api.add_router('/api', r)

urlpatterns = [
    path('admin/', admin.site.urls),
    url(r'^api/', include(('apps.ludan.urls', 'ludan'), namespace='ludan')),
    url(r'^api/', include(('apps.iot.urls', 'iot'), namespace='iot')),
    url(r'^api/', include(('apps.user.urls', 'users'), namespace='users')),
    url(r'^api/', include(('apps.onsite.urls', 'onsite'), namespace='onsite')),
    url(r'^api/', include(('apps.ticket.urls', 'ticket'), namespace='ticket')),
    path('', ninja_api.urls),
    url(r'^$', TemplateView.as_view(template_name="index.html")),
]
