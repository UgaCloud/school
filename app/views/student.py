from django.shortcuts import render, redirect, HttpResponseRedirect, HttpResponse
from django.contrib import messages
from django.urls import reverse
import csv
from django.db import IntegrityError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from app.constants import *
import app.selectors.students as student_selectors
import app.forms.student as student_forms
from app.services.students import register_student, bulk_student_registration, delete_all_csv_files
from app.selectors.model_selectors import *
from app.forms.student import StudentForm
from app.models.students import Student
import app.forms.student as student_forms
import app.selectors.students as student_selectors
import app.selectors.classes as class_selectors
from app.selectors.classes import *
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from app.models import ClassRegister
from django.db.models import Q
from app.models import ClassRegister, AcademicClassStream



@login_required
def manage_student_view(request):
    status = request.GET.get("status", "active")
    page_number = request.GET.get("page", 1)
    per_page = request.GET.get("per_page", 25)
    
    # Get students based on status
    if status == "inactive":
        students_list = student_selectors.get_inactive_students()
    elif status == "all":
        students_list = student_selectors.get_all_students()
    else:
        students_list = student_selectors.get_active_students()
    
    # Paginate the students
    paginator = Paginator(students_list, per_page)
    
    try:
        students = paginator.page(page_number)
    except PageNotAnInteger:
        students = paginator.page(1)
    except EmptyPage:
        students = paginator.page(paginator.num_pages)
    
    student_form = student_forms.StudentForm()
    csv_form = student_forms.StudentRegistrationCSVForm()
    
    context = {
        "students": students,
        "student_form": student_form,
        "csv_form": csv_form,
        "status": status,
        "total_active": student_selectors.get_active_students().count(),
        "total_inactive": student_selectors.get_inactive_students().count(),
        "total_all": student_selectors.get_all_students().count(),
        "per_page": int(per_page),
    }
    
    return render(request, "student/manage_students.html", context)
@login_required
def add_student_view(request):
    if request.method == "POST":
        student_form = student_forms.StudentForm(request.POST, request.FILES)

        if student_form.is_valid():
            _class = student_form.cleaned_data.get("current_class")
            stream = student_form.cleaned_data.get("stream")

            current_academic_year = get_current_academic_year()
            term = get_current_term()
            academic_class = get_current_academic_class(current_academic_year, _class, term)

            class_stream_exists = AcademicClassStream.objects.filter(
                academic_class=academic_class, stream=stream
            ).exists()

            if not class_stream_exists:
                messages.error(request, "No academic class stream found. Student registration aborted.")
                return HttpResponseRedirect(reverse(manage_student_view))  

            student = student_form.save()
            register_student(student, _class, stream)
            messages.success(request, SUCCESS_ADD_MESSAGE)

        else:
            messages.error(request, FAILURE_MESSAGE)

    return HttpResponseRedirect(reverse(manage_student_view))


@login_required
def student_details_view(request, id):
    student = student_selectors.get_student(id)
    context = {
        "student": student,  
    }
    return render(request, "student/student_details.html", context)


    
@login_required
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

@login_required
def bulk_student_registration_view(request):
    delete_all_csv_files()
    if request.method == "POST":
        csv_form = student_forms.StudentRegistrationCSVForm(request.POST, request.FILES)

        if csv_form.is_valid():
            csv_object = csv_form.save()

            try:
                bulk_student_registration(csv_object)  # Now no `request` parameter is passed here
                messages.success(request, SUCCESS_BULK_ADD_MESSAGE)
            except ValueError as e:
                # Catch the ValueError raised from `bulk_student_registration`
                messages.error(request, str(e))  # Display the error message
            except IntegrityError:
                messages.error(request, INTEGRITY_ERROR_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)

    return HttpResponseRedirect(reverse(manage_student_view))

@login_required
def edit_student_view(request, id):
    student = get_model_record(Student, id)

    if request.method == 'POST':
        student_form = StudentForm(request.POST, request.FILES, instance=student)
        if student_form.is_valid():
        
            student_form.save()

            messages.success(request, SUCCESS_ADD_MESSAGE)    
        else:
            messages.error(request, FAILURE_MESSAGE)
        return redirect(add_student_view)
    else:
        student_form = StudentForm(instance=student)

    context = {
        "form": student_form,
        "student": student
    }

    return render(request, "student/edit_student.html", context)

@login_required
def delete_student_view(request, id):
    student = student_selectors.get_student(id)

    student.is_active = False
    student.save()

    messages.success(request, "Student deactivated successfully.")

    return HttpResponseRedirect(reverse(manage_student_view))


@login_required
def classregister(request):
    if request.method =="POST":
        classregisterform= student_forms.ClassRegisterForm(request.POST,request.FILES)
        if classregisterform.is_valid():
            class_register= classregisterform.save()
            messages.success(request,SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request,FAILURE_MESSAGE)
            
        return HttpResponseRedirect(reverse(manage_student_view))
    
    context ={
        "classregisterform":classregisterform,
        "class_register":class_register
    }
    return render(request,"student/class_register.html",context)

#class registration
@login_required
def bulk_register_students(request):
    # Filter active students not yet registered
    registered_students = ClassRegister.objects.values_list('student_id', flat=True)
    unregistered_students = Student.objects.filter(is_active=True).exclude(id__in=registered_students)

    if request.method == "POST":
        selected_students = request.POST.getlist("students")

        # Register selected students
        for student_id in selected_students:
            student = Student.objects.get(id=student_id)

            # Fetch the AcademicClassStream instance
            try:
                academic_class_stream = AcademicClassStream.objects.get(
                    academic_class__Class=student.current_class,  # Match Class
                    stream=student.stream  # Match Stream
                )
            except AcademicClassStream.DoesNotExist:
            
                continue  # or create a new AcademicClassStream

            # Create the ClassRegister entry
            ClassRegister.objects.create(
                academic_class_stream=academic_class_stream,
                student=student,
            )
        messages.success(request,SUCCESS_BULK_ADD_MESSAGE)

        # Redirect after registration
        return redirect(ClassRegister)

    return render(request, "student/bulk_register_students.html", {
        "unregistered_students": unregistered_students,
    })