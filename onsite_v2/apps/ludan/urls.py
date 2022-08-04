from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^ludan/cars/$', views.exportCars),
    url(r'^ludan/columns/$', views.exportColumnSettings),
]
