from django.urls import path

import app.views.index_views as index
from app.views.classes import *
from app.views.school_settings import *
from app.views.student import *
from app.views.subject_views import *
from app.views.staffs_views import *
from app.views.fees_view import *
from app.views.finance import *

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
    
    # Departments
    path('department/', add_department_view, name="add_department_page"),
    path('edit_department/<int:id>/', edit_department_view, name="edit_department"),
    path('delete_department/<int:id>/', delete_department_view, name="delete_department"),
    
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
    
    # Fees
    path('bill_items/', manage_bill_items_view, name="bill_item_page"),
    path('add_bill_item/', add_bill_item_view, name="add_bill_item_page"),
    path('student_bill/', manage_student_bills_view, name="student_bill_page"),
    path('student_bill_details/<int:id>/', manage_student_bill_details_view, name="student_bill_details_page"),
    path('add_student_bill_item/<int:id>/', add_student_bill_item_view, name="add_student_bill_item"),
    path('add_class_bill_item/<int:id>/', add_class_bill_item_view, name="add_class_bill_item"),
    path('record_payment/<int:id>/', add_student_payment_view, name="record_payment"),
    
    # Finance
    path('income_sources/', manage_income_sources, name="income_source_page"),
    path('add_income_source/', add_income_source, name="add_income_source_page"),
    path('edit_income_source/<int:id>/', edit_income_sources, name="edit_income_source"),
    path('delete_income_source/<int:id>/', delete_income_source, name="delete_income_source"),
    
    # Expenses
    path('expenses/', manage_expenses, name="expense_page"),
    path('add_expense/', add_expense, name="add_expense_page"),
    path('edit_expense/<int:id>/', edit_expenses, name="edit_expense"),
    path('delete_expense/<int:id>/', delete_expense, name="delete_expense"),
    
    # Expenditures
    path('expenditures/', manage_expenditures, name="expenditure_page"),
    path('add_expenditure/', add_expenditure, name="add_expenditure_page"),
    path('edit_expenditure/<int:id>/', edit_expenditures, name="edit_expenditure"),
    path('delete_expenditure/<int:id>/', delete_expenditure, name="delete_expenditure"),
    
    # Expenditure Items
    path('items/<int:id>/', manage_expenditure_items, name="items_page"),
    path('add_expenditure_item/', add_expenditure_item, name="add_expenditure_item_page"),
    path('edit_expenditure_item/<int:id>/', edit_expenditure_items, name="edit_expenditure_item"),
    path('delete_expenditure_item/<int:id>/', delete_expenditure_item, name="delete_expenditure_item"),
    
    # Vendors
    path('vendors/', manage_vendors, name="vendor_page"),
    path('add_vendor/', add_vendor, name="add_vendor_page"),
    path('edit_vendor/<int:id>/', edit_vendors, name="edit_vendor"),
    path('delete_vendor/<int:id>/', delete_vendor, name="delete_vendor"),
    
    # Budgets
    path('budgets/', manage_budgets, name="budget_page"),
    path('add_budget/', add_budget, name="add_budget_page"),
    path('edit_budget/<int:id>/', edit_budgets, name="edit_budget"),
    path('delete_budget/<int:id>/', delete_budget, name="delete_budget"),
    
    # Budget Items
    path('budget_items/<int:id>/', manage_budget_items, name="budget_item_page"),
    path('add_budget_item/', add_budget_item, name="add_budget_item_page"),
    path('edit_budget_item/<int:id>/', edit_budget_items, name="edit_budget_item"),
    path('delete_budget_item/<int:id>/', delete_budget_item, name="delete_budget_item"),
]
