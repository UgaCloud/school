from django.urls import path

import app.views.index_views as index
from app.views.classes import *
from app.views.school_settings import *
from app.views.student import *
from app.views.subject_views import *
from app.views.staffs_views import *

urlpatterns = [
    path('', index.index_view, name="index_page"),
    
    # School Details
    path('settings/', settings_page,name="settings_page"),
    path('update_settings/', update_school_settings, name="update_settings_page"),
    
    # Sections
    path('sections/', school_section_view, name="section_page"),
    path('edit_section/<int:id>/', edit_section_view, name="edit_section"),
    path('delete_section/<int:id>/', delete_section_view, name="delete_section"),
    
    #Signatures
    path('signature/', add_signature_view, name="add_signature_page"),
    path('edit_signature/<int:id>/', edit_signature_view, name="edit_signature"),
    path('delete_signature/<int:id>/', delete_signature_view, name="delete_signature"),
    
    # Classes
    path('classes/', class_view, name="class_page"),
    
    # Stream
    path('stream/', stream_view, name="stream_page"),
    path('delete_stream/<int:id>/', delete_stream_view, name="delete_stream"),
    
    # Academic Class
    path('academic_classes/', academic_class_view, name="academic_class_page"),
    path('academic_class_details/<int:id>/', academic_class_details_view, name="academic_class_details_page"),path('add_class_stream/<int:id>/', add_class_stream, name="add_class_stream_page"),
    
    # Student
    path('students/', manage_student_view, name="student_page"),
    path('add_student/', add_student_view, name="add_student"),
    path('download_student_template/', download_student_template_csv, name="download_student_template"),
    path('bulk_student_registration/', bulk_student_registration_view, name="bulk_student_registration"),
    
    # Subject
    path('subjects/', manage_subjects_view, name="subjects_page"),
    path('add_subject/', add_subject_view, name="add_subject_page"),
    path('edit_subject/<int:id>/', edit_subject_view, name="edit_subject_page"),
    path('delete_subject/<int:id>/', delete_subject_view, name="delete_subject_page"),
    
    # Staff
    path('staffs/', manage_staff_view, name="staff_page"),
    path('add_staff/', add_staff, name="add_staff"),
    path('staff_details/<int:id>/', staff_deitals_view, name="staff_details_page"),
]
