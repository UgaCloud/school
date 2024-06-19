from django.urls import path

import app.views.index_views as index
import app.views.classes as classes
import app.views.school_settings as school_settings

urlpatterns = [
    path('', index.index_view, name="index_page"),
    
    # School Details
    path('settings/', school_settings.settings_page, name="settings_page"),
    path('update_settings/', school_settings.update_school_settings, name="update_settings_page"),
    
    # Sections
    path('sections/', school_settings.school_section_view, name="section_page"),
    path('edit_section/<int:id>/', school_settings.edit_section_view, name="edit_section"),
    path('delete_section/<int:id>/', school_settings.delete_section_view, name="delete_section"),
    
    #Signatures
    path('signature/', school_settings.add_signature_view, name="add_signature_page"),
    path('edit_signature/<int:id>/', school_settings.edit_signature_view, name="edit_signature"),
    path('delete_signature/<int:id>/', school_settings.delete_signature_view, name="delete_signature"),
    
    # Classes
    path('classes/', classes.class_view, name="class_page"),
    
    # Stream
    path('stream/', classes.stream_view, name="stream_page"),
    path('delete_stream/<int:id>/', classes.delete_stream_view, name="delete_stream"),
    
    # Academic Class
    path('academic_classes/', classes.academic_class_view, name="academic_class_page"),
    path('academic_class_details/<int:id>/', classes.academic_class_details_view, name="academic_class_details_page"),path('add_class_stream/', classes.add_class_stream, name="add_class_stream_page"),
]
