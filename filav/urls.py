"""filav URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin

from fila.views import *
from rest_framework import routers
from django.contrib.auth import views as auth_views

router = routers.DefaultRouter()
router.register(r'filas', FilaViewSet)
router.register(r'locais', LocalViewSet)
router.register(r'turnos', TurnoViewSet)
router.register(r'cliente/turnos/ativos', ClienteTurnosAtivosViewSet)

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^fila/cliente/', ClienteView.as_view(), name='cliente'),
    url(r'^fila/scanner/', ScannerView.as_view(), name='scanner'),
    url(r'^accounts/login/$', auth_views.login, name='login'),
    url(r'^logout/$', auth_views.logout, {'next_page': 'login'}, name='logout'),
    url(r'^oauth/', include('social_django.urls', namespace='social')),
    url(r'^api/', include(router.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]
