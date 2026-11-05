from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from pantry import views as pantry_views

urlpatterns = [
    path('manifest.json', pantry_views.manifest_json_view, name='manifest_json'),
    path('sw.js', pantry_views.service_worker_view, name='service_worker'),
    path('admin/', admin.site.urls),
    path('', include('pantry.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
