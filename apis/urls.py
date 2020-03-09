from django.conf.urls import url
from django.urls import path

from apis import views

urlpatterns = [
    url(r'^login$', views.login),
    url(r'^user_info$', views.user_info),
    url(r'^update$', views.set_service_feature),
    url(r'^logout$', views.logout),
]
