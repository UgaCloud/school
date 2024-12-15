from django.shortcuts import render, redirect, HttpResponseRedirect,get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.forms import modelformset_factory
from app.constants import *
from app.models.results import AssessmentType,AnnualResult,Assessment,GradingSystem,Result
from app.forms.results import AssesmentTypeForm,GradingSystemForm,ResultForm,AssessmentForm
from app.selectors.model_selectors import *
from app.models import *
from app.selectors.model_selectors import *
from django.db import transaction
from django.db.models import Avg, Sum, F,Q,Count
from app.utils.utils import calculate_grade_and_points
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from django.shortcuts import get_object_or_404
from io import BytesIO
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
import tempfile



# Add Results View
@login_required
def add_results_view(request, assessment_id=None):
    if assessment_id is None:
        return redirect('class_assessment_list')
    assessment = Assessment.objects.get(id=assessment_id)
    academic_class = assessment.academic_class
    class_registers = ClassRegister.objects.filter(academic_class_stream__academic_class=academic_class)
    students = [class_register.student for class_register in class_registers]
    ResultFormSet = modelformset_factory(Result, form=ResultForm, extra=len(students))

    if request.method == "POST":
       with transaction.atomic():
        formset = ResultFormSet(request.POST)
        if formset.is_valid():
            for i, form in enumerate(formset):
                form.instance.assessment = assessment
                form.instance.student_id = students[i].id
            formset.save()
            messages.success(request, SUCCESS_BULK_ADD_MESSAGE)
            return redirect('list_assessments', class_id=academic_class.id)  
        else:
            messages.error(request, FAILURE_MESSAGE)
    else:
        formset = ResultFormSet(queryset=Result.objects.filter(assessment=assessment))

    zipped_forms = list(zip(formset.forms, students))

    context = {
        'assessment': assessment,
        'formset': formset,
        'zipped_forms': zipped_forms,
    }
    return render(request, 'results/add_results_page.html', context)

#Edit Results view
@login_required
def edit_results_view(request, assessment_id=None, student_id=None):
    if assessment_id is None:
        return redirect(list_assessments_view)
    assessment = Assessment.objects.get(id=assessment_id)
    academic_class = assessment.academic_class
    class_registers = ClassRegister.objects.filter(academic_class_stream__academic_class=academic_class)
    students = [class_register.student for class_register in class_registers]

    if student_id is not None:
        student = get_object_or_404(Student, id=student_id)
        results = Result.objects.filter(assessment=assessment, student=student)
    else:
        results = Result.objects.filter(assessment=assessment)

    ResultFormSet = modelformset_factory(Result, form=ResultForm, extra=0)

    if request.method == "POST":
        with transaction.atomic():
            formset = ResultFormSet(request.POST)
            if formset.is_valid():
                for form in formset:
                    form.instance.assessment = assessment
                    if student_id is not None:
                        form.instance.student = student
                formset.save()
                messages.success(request, SUCCESS_EDIT_MESSAGE)
                return redirect('add_results', assessment_id=assessment_id) 
            else:
                messages.error(request, FAILURE_MESSAGE)
    else:
        formset = ResultFormSet(queryset=results)

    if student_id is not None:
        zipped_forms = list(zip(formset.forms, [student]))
    else:
        zipped_forms = list(zip(formset.forms, students))

    context = {
        'assessment': assessment,
        'formset': formset,
        'zipped_forms': zipped_forms,
    }
    return render(request, 'results/edit_results_page.html', context)

@login_required
def class_assessment_list_view(request):
    classes =Class.objects.all()
    return render(request,'results/class_assessments.html',{'classes':classes})

#List of Assessments basing on specific academic_class

def list_assessments_view(request, class_id):
    academic_class = AcademicClass.objects.get(id=class_id)
    print(academic_class)
    assessments = Assessment.objects.filter(academic_class=academic_class)
    return render(request, 'results/list_assessments.html', {'assessments': assessments, 'class_id': class_id})

#Grading System

def grading_system_view(request):
    if request.method == "POST":
        grading_form = GradingSystemForm(request.POST)
        if grading_form.is_valid():
            grading_form.save()
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)

    
    grading_form = GradingSystemForm()

    grading_systems = GradingSystem.objects.all()  

    context = {
        'grading_form': grading_form,  
        'grading_systems': grading_systems,  
    }

    return render(request, 'results/grading_system.html', context)


#Edit grading system

def edit_grading_system_view(request, id):
    grading_system = get_model_record(GradingSystem,id)

    if request.method == "POST":
        grading_form = GradingSystemForm(request.POST, instance=grading_system)
        
        if grading_form.is_valid():
            grading_form.save()
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
        return redirect(grading_system_view)

    else:
        grading_form = GradingSystemForm(instance=grading_system)
    
    context = {
        "grading_form": grading_form,
        "grading_system": grading_system
    }
    
    return render(request, 'results/edit_grading_system.html', context)


def delete_grading_system_view(request, id):
    grading_system = GradingSystem.objects.get(pk=id)
    
    grading_system.delete()
    messages.success(request, DELETE_MESSAGE)
    return redirect(grading_system_view)


def assessment_list_view(request):
    assessments = Assessment.objects.all()
    context = {
        'assessments': assessments,
    }
    return render(request, 'results/assessment_list.html', context)


def add_assessment_view(request):
    if request.method == "POST":
        form = AssessmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,SUCCESS_ADD_MESSAGE)
            
              
    
    form = AssessmentForm()
    assessment = Assessment.objects.all()
    
    context = {
        'form': form,
        'assessments':assessment,
    }
    return render(request,'results/add_assessment.html',context)

@login_required
def edit_assessment(request, id):
    assessment = get_model_record(Assessment,id)
    if request.method == "POST":
        form = AssessmentForm(request.POST, instance=assessment)
        if form.is_valid():
            form.save()
            messages.success(request,SUCCESS_ADD_MESSAGE)
            return redirect(add_assessment_view)
            
        else:
            messages.error(request,FAILURE_MESSAGE)
        
    else:
        form = AssessmentForm(instance=assessment)
    
    context = {
        'form': form,
        'assessment':assessment
    }
    return render(request, 'results/edit_assessment.html', context)

@login_required
def delete_assessment_view(request,id):
    assessment = get_model_record(Assessment,id)
    assessment.delete()
    messages.success(request, DELETE_MESSAGE)
    return HttpResponseRedirect(reverse(add_assessment_view))

















def assesment_type_view(request):
    if request.method == "POST":
        assesment_type_form = AssesmentTypeForm(request.POST)
        
        if assesment_type_form.is_valid():
            assesment_type_form.save()
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
         
            messages.error(request,FAILURE_MESSAGE)
    
    assesment_type_form = AssesmentTypeForm()
    
    assesment_type = AssessmentType.objects.all()
    
    context = {
        "form": assesment_type_form,
        "assesment_type": assesment_type
    }
    
    return render(request, "results/assesment_type.html", context)

def edit_assesment_type(request,id):
    assesment_type = get_model_record(AssessmentType,id)
    if request.method =="POST":
       assesment_type_form = AssesmentTypeForm(request.POST,instance=assesment_type)
       if assesment_type_form.is_valid():
           assesment_type_form.save().save()
           messages.success(request,SUCCESS_ADD_MESSAGE)
           return redirect(assesment_type_view)
       else:
           messages.error(request,FAILURE_MESSAGE)
           
    else:
        assesment_type_form = AssesmentTypeForm(instance=assesment_type)
    context={
        "form":assesment_type_form,
        "assesment_type":assesment_type
    } 
    return render(request,"results/edit_assesment_type.html",context)

def delete_assesment_view(request, id):
    assesment_type = AssessmentType.objects.get(pk=id)
    
    assesment_type.delete()
    messages.success(request, DELETE_MESSAGE)
    
    return redirect(assesment_type_view)



def get_grade_and_points(final_score):
    grading_system = GradingSystem.objects.all()
    
    for grade in grading_system:
        if grade.min_score <= final_score <= grade.max_score:
            return grade.grade, grade.points
    
    return "F9", 9

def get_student_results(class_id=None, student_id=None):
    results = Result.objects.select_related(
        'assessment', 'student', 'assessment__assessment_type', 'assessment__subject'
    )
    
    # Filter by class if provided
    if class_id:
        results = results.filter(student__current_class__academicclass__id=class_id)
    
    # Filter by student if provided
    if student_id:
        results = results.filter(student_id=student_id)

    student_results = {}

    for result in results:
        student_name = result.student.student_name
        student_id = result.student.id  # Capture the student ID
        subject_name = result.assessment.subject.name
        assessment_type = result.assessment.assessment_type.name

        if student_name not in student_results:
            student_results[student_name] = {'student_id': student_id}

        if subject_name not in student_results[student_name]:
            student_results[student_name][subject_name] = {
                'BOT': 0,
                'MOT': 0,
                'EOT': 0,
                'final_score': 0,
                'grade': None,
                'points': 0
            }

        if assessment_type == 'BOT':
            student_results[student_name][subject_name]['BOT'] = result.actual_score
        elif assessment_type == 'MOT':
            student_results[student_name][subject_name]['MOT'] = result.actual_score
        elif assessment_type == 'EOT':
            student_results[student_name][subject_name]['EOT'] = result.actual_score

    # Calculate grades and totals
    for student_name, subjects in student_results.items():
        total_final_score = 0
        total_points = 0

        for subject_name, data in subjects.items():
            if subject_name != 'student_id':
                final_score = data['BOT'] + data['MOT'] + data['EOT']
                final_score = min(final_score, 100)
                data['final_score'] = int(round(final_score))

                grade, points = get_grade_and_points(data['final_score'])
                data['grade'] = grade
                data['points'] = points

                total_final_score += data['final_score']
                total_points += data['points']

        student_results[student_name]['total_final_score'] = total_final_score
        student_results[student_name]['total_points'] = total_points

    return student_results

def result_list(request):
    class_id = request.GET.get('Class_id')
    selected_class_id = class_id

    classes = AcademicClass.objects.all()
    student_results = get_student_results(class_id=class_id)

    return render(request, 'results/results_list.html', {
        'student_results': student_results,
        'classes': classes,
        'selected_class_id': selected_class_id,
    })

# def student_report_card(request, student_id):
#     student_results = get_student_results(student_id=student_id)

#     return render(request, 'results/student_report.html', {
#         'student_results': student_results,
#     })




def student_report_card(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    results = Result.objects.filter(student=student)

    # Get the current term
    current_term = Term.objects.filter(is_current=True).select_related('academic_year').first()
    
    # Organize report data
    report_data = {}
    total_final_score = 0
    total_points = 0

    for result in results:
        assessment = result.assessment
        assessment_type = assessment.assessment_type.name
        subject_name = assessment.subject.name

        if subject_name not in report_data:
            report_data[subject_name] = {'BOT': 0, 'MOT': 0, 'EOT': 0, 'final_score': 0, 'grade': None, 'points': 0}

        if assessment_type == 'BOT':
            report_data[subject_name]['BOT'] = result.actual_score
        elif assessment_type == 'MOT':
            report_data[subject_name]['MOT'] = result.actual_score
        elif assessment_type == 'EOT':
            report_data[subject_name]['EOT'] = result.actual_score

        final_score = (
            report_data[subject_name]['BOT'] +
            report_data[subject_name]['MOT'] +
            report_data[subject_name]['EOT']
        )
        final_score = min(final_score, 100)
        grade, points = get_grade_and_points(final_score)

        report_data[subject_name]['final_score'] = int(round(final_score))
        report_data[subject_name]['grade'] = grade
        report_data[subject_name]['points'] = points

        total_final_score += final_score
        total_points += points

    return render(request, 'results/student_report_card.html', {
        'student': student,
        'report_data': report_data,
        'total_final_score': total_final_score,
        'total_points': total_points,
        'current_term': current_term,
    })



def generate_termly_report_pdf(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    results = Result.objects.filter(student=student)

    # Get the current term
    current_term = Term.objects.filter(is_current=True).select_related('academic_year').first()
    
    # Organize report data
    report_data = {}
    total_final_score = 0
    total_points = 0

    for result in results:
        assessment = result.assessment
        assessment_type = assessment.assessment_type.name
        subject_name = assessment.subject.name

        if subject_name not in report_data:
            report_data[subject_name] = {'BOT': 0, 'MOT': 0, 'EOT': 0, 'final_score': 0, 'grade': None, 'points': 0}

        if assessment_type == 'BOT':
            report_data[subject_name]['BOT'] = result.actual_score
        elif assessment_type == 'MOT':
            report_data[subject_name]['MOT'] = result.actual_score
        elif assessment_type == 'EOT':
            report_data[subject_name]['EOT'] = result.actual_score

        final_score = (
            report_data[subject_name]['BOT'] +
            report_data[subject_name]['MOT'] +
            report_data[subject_name]['EOT']
        )
        final_score = min(final_score, 100)
        grade, points = get_grade_and_points(final_score)

        report_data[subject_name]['final_score'] = int(round(final_score))
        report_data[subject_name]['grade'] = grade
        report_data[subject_name]['points'] = points

        total_final_score += final_score
        total_points += points

    # Render the HTML content
    html_string = render_to_string('results/student_report_card.html', {
        'student': student,
        'report_data': report_data,
        'total_final_score': total_final_score,
        'total_points': total_points,
        'current_term': current_term,
    })

    # Create a response object for the PDF output
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{student.student_name}_Termly_Report.pdf"'

    # Create PDF from HTML using xhtml2pdf (Pisa)
    pdf_output = BytesIO()
    pisa_status = pisa.CreatePDF(html_string, dest=pdf_output)

    if pisa_status.err:
        return HttpResponse('We had some errors while generating your PDF', status=400)

    pdf_output.seek(0)
    response.write(pdf_output.read())
    return response
