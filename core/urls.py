from django.contrib import admin
from django.urls import path,include

from django.conf.urls.static import static
from core.settings import common

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('app.urls')),
    
]

urlpatterns += static(common.MEDIA_URL, document_root=common.MEDIA_ROOT)
