from django.urls import path

import app.views.index_views as index_views

urlpatterns = [
    path('', index_views.index_view, name="index_page"),
]
