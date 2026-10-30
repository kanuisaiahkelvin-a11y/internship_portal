from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from .views import service_worker

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('opportunities/', include('opportunities.urls')),
    path('applications/', include('applications.urls')),
    path('notifications/', include('notifications.urls')),

    # Installable web app (PWA).
    path('sw.js', service_worker, name='service_worker'),
    path(
        'offline/',
        TemplateView.as_view(template_name='pwa/offline.html'),
        name='offline',
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
