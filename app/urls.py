from django.urls import path
from django.contrib.auth import views as auth_views
import app.views.index_views as index
from app.views.classes import *
from app.views.school_settings import *
from app.views.student import *
from app.views.subject_views import *
from app.views.staffs_views import *
from app.views.fees_view import *
from app.views.finance import *
from app.views.results import *
from app.views.accounts import *
from app.views.timetables import *



urlpatterns = [
    path('index/', index.index_view, name="index_page"),
    
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
    
    #Departments
    path('department/', add_department_view, name="add_department_page"),
    path('edit_department/<int:id>/', edit_department_view, name="edit_department"),
    path('delete_department/<int:id>/', delete_department_view, name="delete_department"),
    
    #Classes
    path('classes/', class_view, name="class_page"),
    path('edit_class/<int:id>/', edit_classe_view,name="edit_class"),
    path('delete_class/<int:id>/',delete_class_view, name="delete_class"),
    path('class-stream/edit/<int:id>/', edit_class_stream, name="edit_class_stream"),
    path('class-stream/delete/<int:id>/', delete_class_stream, name="delete_class_stream"),

    
    
    #Stream
    path('stream/', stream_view, name="stream_page"),
    path('edit_stream/<int:id>/',edit_stream, name="edit_stream"),
    path('delete_stream/<int:id>/', delete_stream_view, name="delete_stream"),
   
    #Academic Class
    path('academic_classes/', academic_class_view, name="academic_class_page"),
    path('academic_class_details/<int:id>/', academic_class_details_view, name="academic_class_details_page"),
    path('add_class_stream/<int:id>/', add_class_stream, name="add_class_stream_page"),
    path('edit_academic_class_details/<int:id>/', edit_academic_class_details_view,name="edit_academic_class_details_page"),
    path('delete_academic_class/<int:id>/',delete_academic_class_view,name="delete_academic_class"),
    
   #Student
    path('students/', manage_student_view, name="student_page"),
    path('add_student/', add_student_view, name="add_student"),
    path('student_details/<int:id>/', student_details_view, name="student_details_page"),
    path('download_student_template/', download_student_template_csv, name="download_student_template"),
    path('bulk_student_registration/', bulk_student_registration_view, name="bulk_student_registration"),
    path('edit_student/<int:id>/', edit_student_view, name="edit_student_page"),
    path('delete_student/<int:id>/', delete_student_view, name="delete_student_page"),
    path("register/", bulk_register_students, name="bulk_register_students"),# student registration in classes
    
    
    #Subject
    path('subjects/', manage_subjects_view, name="subjects_page"),
    path('add_subject/', add_subject_view, name="add_subject_page"),
    path('edit_subject/<int:id>/', edit_subject_view, name="edit_subject_page"),
    path('delete_subject/<int:id>/', delete_subject_view, name="delete_subject_page"),
    
    #Subject Allocation
    path('subject_allocation/', add_class_subject_allocation, name="subject_allocation_page"),
    path('subject_allocation_list/',class_subject_allocation_list,name= "class_subject_allocation_page"),
    path('edit_subject_allocation/<int:id>/',edit_subject_allocation_view, name="edit_subject_allocation_page"),
    path('delete_subject_allocation/<int:id>/',delete_class_subject_allocation, name="delete_subject_allocation"),
    
    #Staff
    path('staff/<int:id>/upload-document/', staff_details_view, name='upload_staff_document'),
    path('staffs/', manage_staff_view, name="staff_page"),
    path('add_staff/', add_staff, name="add_staff"),
    path('staff_details/<int:id>/', staff_details_view, name="staff_details_page"),
    path('edit_staff_details/<int:id>/', edit_staff_details_view, name="edit_staff_details_page"),
    path('delete_staff/<int:id>/', delete_staff_view, name="delete_staff_page"),
    path('staff/document/delete/<int:id>/', delete_staff_document, name='delete_staff_document'),

    
    #Fees
    path('bill_items/', manage_bill_items_view, name="bill_item_page"),
    path('add_bill_item/', add_bill_item_view, name="add_bill_item_page"),
    path('edit_bill_item/<int:id>/', edit_bill_item_view, name="edit_bill_item_page"),
    path('delete_bill_item/<int:id>/',delete_bill_item_view, name="delete_bill_item_page"), 
    path('student_bill/', manage_student_bills_view, name="student_bill_page"),
    path('student_bill_details/<int:id>/', manage_student_bill_details_view, name="student_bill_details_page"),
    path('add_student_bill_item/<int:id>/', add_student_bill_item_view, name="add_student_bill_item"),
    path('add_class_bill_item/<int:id>/add-bill/', add_class_bill_item_view, name="add_class_bill_items"),
    path('record_payment/<int:id>/', add_student_payment_view, name="record_payment"),
    path("class-bills/", class_bill_list_view, name="class_bill_list"),
    path('class/bill-item/<int:id>/edit/', edit_class_bill_item_view, name="edit_class_bill_item"),
    path('delete_class_bill_item/<int:id>/', delete_class_bill_item_view, name='delete_class_bill_item'),
    path('fees-status/', student_fees_status_view, name='fees_status'),

    
    #Finance
    path('income_sources/', manage_income_sources, name="income_source_page"),
    path('add_income_source/', add_income_source, name="add_income_source_page"),
    path('edit_income_source/<int:id>/', edit_income_sources, name="edit_income_source"),
    path('delete_income_source/<int:id>/', delete_income_source, name="delete_income_source"),
    
    #Expenses
    path('expenses/', manage_expenses, name="expense_page"),
    path('add_expense/', add_expense, name="add_expense_page"),
    path('edit_expense/<int:id>/', edit_expenses, name="edit_expense"),
    path('delete_expense/<int:id>/', delete_expense, name="delete_expense"),
    
    #Expenditures
    path('expenditures/', manage_expenditures, name="expenditure_page"),
    path('add_expenditure/', add_expenditure, name="add_expenditure_page"),
    path('edit_expenditure/<int:id>/', edit_expenditures, name="edit_expenditure"),
    path('expenditure/edit/<int:id>/', edit_expenditures, name='edit_expenditure'),
    path('delete_expenditure/<int:id>/', delete_expenditure, name="delete_expenditure"),
     
    #Expenditure Items
    path('items/<int:id>/', manage_expenditure_items, name="items_page"),
    path('add_expenditure_item/', add_expenditure_item, name="add_expenditure_item_page"),
    path('edit_expenditure_item/<int:id>/', edit_expenditure_items, name="edit_expenditure_item"),
    path('delete_expenditure_item/<int:id>/', delete_expenditure_item, name="delete_expenditure_item"),
    
    #Vendors
    path('vendors/', manage_vendors, name="vendor_page"),
    path('add_vendor/', add_vendor, name="add_vendor_page"),
    path('edit_vendor/<int:id>/', edit_vendors, name="edit_vendor"),
    path('delete_vendor/<int:id>/', delete_vendor, name="delete_vendor"),
    
    #Budgets
    path('budgets/', manage_budgets, name="budget_page"),
    path('add_budget/', add_budget, name="add_budget_page"),
    path('edit_budget/<int:id>/', edit_budgets, name="edit_budget"),
    path('delete_budget/<int:id>/', delete_budget, name="delete_budget"),
    
    #Budget Items
    path('budget_items/<int:id>/', manage_budget_items, name="budget_item_page"),
    path('add_budget_item/', add_budget_item, name="add_budget_item_page"),
    path('edit_budget_item/<int:id>/', edit_budget_items, name="edit_budget_item"),
    path('delete_budget_item/<int:id>/', delete_budget_item, name="delete_budget_item"),
    
    #Results
    path('add_grading_system/', grading_system_view, name='add_grading_system_page'),
    path('edit_grading_system/<int:id>/', edit_grading_system_view, name="edit_grading_system"),
    path('delete_grading_system/<int:id>/', delete_grading_system_view, name="delete_grading_system"),
    path('add_results/',add_results_view,name="add_results_page"),
    path('add_results/<int:assessment_id>/', add_results_view, name='add_results'),
    path('edit_results/<int:assessment_id>/<int:student_id>/edit_results/', edit_results_view, name='edit_results_view'),
    path('classes_assessments/',class_assessment_list_view,name='class_assessment_list'),
    path('classes_assessments/<int:class_id>/assessments/',list_assessments_view,name='list_assessments'),
    path("class-student-filter/", class_result_filter_view, name="class_stream_filter"),
    path("student/<int:student_id>/performance/", student_performance_view, name="student_performance"),
    path("student/<int:student_id>/export-pdf/", export_student_pdf, name="export_student_pdf"),
    




    #Assessment
    path('assessments/', assessment_list_view, name='assessment_list'), 
    path('assessments/create/', add_assessment_view, name='assessment_create'),
    path('edit_assessments/<int:id>/', edit_assessment, name='edit_assessment_page'),
    path('delete_assessments/<int:id>/', delete_assessment_view, name='delete_assessment'), 
    path('assesment_type/',assesment_type_view, name="assesment_type_page"),
    path('edit_assesment_type/<int:id>/', edit_assesment_type, name="edit_assesment_type"),
    path('delete_assesment_type/<int:id>/', delete_assesment_view, name="delete_assesment_type"),

    #Authentication
    path('', user_login, name='login'),
    path('dashboard/', dashboard, name='dashboard'),
    path('switch-role/', switch_role, name='switch_role'),
    path('logout/', logout_view, name='logout'),
    path('users/', UserListView.as_view(), name='user_list'),
    path('users/<int:pk>/',UserDetailView.as_view(), name='user_detail'),
    path('create-account/',create_account_view, name='create_account'),
    path('users/delete/<int:id>/',delete_user_view, name='delete_user'),
    path('password_change/',password_change_view, name='password_change'),

    #Reset Password
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Timetables
    path('timetable-center/', timetable_center, name='timetable_center'),
    path('teacher/timetable/', teacher_timetable_view, name='teacher_timetable'),
]



    


    

    





