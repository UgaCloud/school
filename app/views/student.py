from django.shortcuts import render, redirect, HttpResponseRedirect, HttpResponse
from django.contrib import messages
from django.urls import reverse
import csv
from django.db import IntegrityError

from app.constants import *
import app.selectors.students as student_selectors
import app.forms.student as student_forms
from app.services.students import register_student, bulk_student_registration, delete_all_csv_files

def manage_student_view(request):
    students = student_selectors.get_all_students()
    
    student_form = student_forms.StudentForm()
    csv_form = student_forms.StudentRegistrationCSVForm()
    
    context = {
        "students": students,
        "student_form": student_form,
        "csv_form": csv_form
    }
    
    return render(request, "student/manage_students.html", context)

def add_student_view(request):
    if request.method == "POST":
        student_form = student_forms.StudentForm(request.POST, request.FILES)
        
        if student_form.is_valid():
            student = student_form.save()
            
            register_student(student, student.current_class, student.stream)
            
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
    
    return HttpResponseRedirect(reverse(manage_student_view))

def download_student_template_csv(request):
    response = HttpResponse(content_type='text/csv')
    
    # Name the csv file
    filename = "students_template.csv"
    response['Content-Disposition'] = 'attachment; filename=' + filename
    
    writer = csv.writer(response, delimiter=',')
    
    # Writing the first row of the csv
    heading_text = "Student Registration Data"
    writer.writerow([heading_text.upper()])
    
    writer.writerow(
        ['ID No', 'Student Name', 'Gender', 'Birth Date(dd/mm/yy)', 'Nationality', 'Religion', 'Address',
         'Guardian', 'Relationship', 'Guardian Contact', 'Academic year', 'Current Class', 'Stream', 'Term'])

    # Return the response
    return response

def bulk_student_registration_view(request):
    
    delete_all_csv_files()
    if request.method == "POST":
        csv_form = student_forms.StudentRegistrationCSVForm(request.POST, request.FILES)
        
        if csv_form.is_valid():
            csv_object = csv_form.save()
            
            try:
                bulk_student_registration(csv_object)
                messages.success(request, SUCCESS_BULK_ADD_MESSAGE)
            except(ValueError, IntegrityError):
                if ValueError:
                    messages.error(request, INVALID_VALUE_MESSAGE)
                elif IntegrityError:
                    messages.error(request, INTEGRITY_ERROR_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
    
    return HttpResponseRedirect(reverse(manage_student_view))
