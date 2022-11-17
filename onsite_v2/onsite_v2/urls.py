from django.conf.urls import url
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    url(r'^api/', include(('apps.ludan.urls', 'ludan'), namespace='ludan')),
    url(r'^api/', include(('apps.iot.urls', 'iot'), namespace='iot')),
    url(r'^api/', include(('apps.user.urls', 'users'), namespace='users')),
    url(r'^api/', include(('apps.onsite.urls', 'onsite'), namespace='onsite')),
    url(r'^api/', include(('apps.ticket.urls', 'ticket'), namespace='ticket')),
    url(r'^$', TemplateView.as_view(template_name="index.html")),
]
