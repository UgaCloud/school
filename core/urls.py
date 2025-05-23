from django.contrib import admin
from django.urls import path,include

from django.conf.urls.static import static
from core.settings import common

import debug_toolbar

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('app.urls')),
    path('__debug__/', include(debug_toolbar.urls)),
    
]

urlpatterns += static(common.MEDIA_URL, document_root=common.MEDIA_ROOT)
