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
from django.shortcuts import get_object_or_404
from io import BytesIO
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
import tempfile
from decimal import Decimal, InvalidOperation,ROUND_HALF_UP
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import A4
from django.utils import timezone
from django.core.paginator import Paginator
from app.selectors.results import get_grade_and_points, get_current_mode,get_performance_metrics, get_grade_from_average
from app.utils.pdf_utils import generate_student_report_pdf
from collections import defaultdict
import logging
logger = logging.getLogger(__name__)



@login_required
def add_results_view(request, assessment_id=None):
    if not assessment_id:
        return redirect('class_assessment_list')

    assessment = get_object_or_404(Assessment, id=assessment_id)
    academic_class = assessment.academic_class

    class_registers = ClassRegister.objects.filter(academic_class_stream__academic_class=academic_class)
    students = [register.student for register in class_registers]

    existing_results = Result.objects.filter(assessment=assessment)
    existing_students = {result.student_id for result in existing_results}
    students_without_results = [student for student in students if student.id not in existing_students]

    current_mode = ResultModeSetting.get_mode()

    if request.method == "POST":
        if "edit_result" in request.POST:
            result_id = request.POST.get("edit_result")
            result = get_object_or_404(Result, id=result_id, assessment=assessment)
            score = request.POST.get(f'score_{result.student.id}')
            try:
                result.score = Decimal(score)
                result.save()
                messages.success(request, f"Result for {result.student} updated successfully!")
            except (ValueError, TypeError, InvalidOperation):
                messages.error(request, f"Invalid score entered for {result.student}.")
            return redirect('add_results', assessment_id=assessment.id)

        elif "add_results" in request.POST:
            with transaction.atomic():
                bulk_results = []
                for student in students_without_results:
                    score = request.POST.get(f'score_{student.id}')
                    if score:
                        try:
                            score = Decimal(score)
                            bulk_results.append(Result(
                                assessment=assessment,
                                student=student,
                                score=score
                            ))
                        except (ValueError, TypeError, InvalidOperation):
                            messages.error(request, f"Invalid score for {student}.")
                            return redirect('add_results', assessment_id=assessment.id)

                Result.objects.bulk_create(bulk_results)
                messages.success(request, "New results added successfully!")
            return redirect('add_results', assessment_id=assessment.id)

    context = {
        'assessment': assessment,
        'students_without_results': students_without_results,
        'existing_results': existing_results,
        'current_mode': current_mode,
    }
    return render(request, 'results/add_results_page.html', context)


@login_required
def edit_results_view(request, assessment_id=None, student_id=None):
    if not assessment_id:
        return redirect('class_assessment_list')

    assessment = get_object_or_404(Assessment, id=assessment_id)
    academic_class = assessment.academic_class
    class_registers = ClassRegister.objects.filter(academic_class_stream__academic_class=academic_class)
    all_students = [register.student for register in class_registers]

    if student_id:
        student = get_object_or_404(Student, id=student_id)
        results = Result.objects.filter(assessment=assessment, student=student)
        form_students = [student]
    else:
        results = Result.objects.filter(assessment=assessment)
        form_students = all_students

    ResultFormSet = modelformset_factory(Result, form=ResultForm, extra=0)

    if request.method == "POST":
        formset = ResultFormSet(request.POST, queryset=results)
        if formset.is_valid():
            with transaction.atomic():
                for form in formset:
                    form.instance.assessment = assessment
                    if student_id:
                        form.instance.student = student
                formset.save()
                messages.success(request, "Results updated successfully!")
                return redirect('add_results', assessment_id=assessment_id)
        else:
            messages.error(request, "There was a problem with your input. Please check the form.")
    else:
        formset = ResultFormSet(queryset=results)

    zipped_forms = zip(formset.forms, form_students)
    current_mode = ResultModeSetting.get_mode()

    context = {
        'assessment': assessment,
        'formset': formset,
        'zipped_forms': zipped_forms,
        'current_mode': current_mode,
    }
    return render(request, 'results/edit_results_page.html', context)



@login_required
def class_assessment_list_view(request):
    if request.user.is_superuser:
        # Admin sees all classes
        classes = Class.objects.all()
    else:
        try:
            # Get the staff account for the logged-in user
            staff_account = StaffAccount.objects.get(user=request.user)

            # Get the AcademicClassStream objects allocated to the teacher
            teacher_allocations = ClassSubjectAllocation.objects.filter(subject_teacher=staff_account.staff)
            allocated_streams = AcademicClassStream.objects.filter(
                id__in=teacher_allocations.values_list('academic_class_stream', flat=True)
            )

            # Get the academic classes from these streams
            allocated_classes = AcademicClass.objects.filter(
                id__in=allocated_streams.values_list('academic_class', flat=True)
            )
            classes = Class.objects.filter(
                id__in=allocated_classes.values_list('Class', flat=True)
            ).distinct()
        except StaffAccount.DoesNotExist:
            classes = Class.objects.none()

    return render(request, 'results/class_assessments.html', {'classes': classes})


#List of Assessments basing on specific academic_class
@login_required
def list_assessments_view(request, class_id):
    academic_class = get_object_or_404(AcademicClass, id=class_id)
    # Get the staff account for the logged-in user
    staff_account = StaffAccount.objects.filter(user=request.user).first()
    if request.user.is_superuser:
        assessments = Assessment.objects.filter(academic_class=academic_class)
    else:
        if staff_account:
            # Get the class subject allocations for the logged-in teacher for the specific class
            teacher_allocations = ClassSubjectAllocation.objects.filter(
                subject_teacher=staff_account.staff,
                academic_class_stream__academic_class=academic_class
            )

            # If the teacher is assigned to any subject in this class, fetch the corresponding assessments
            if teacher_allocations.exists():
                subject_ids = teacher_allocations.values_list('subject', flat=True)
                assessments = Assessment.objects.filter(
                    academic_class=academic_class,
                    subject__in=subject_ids
                )
            else:
                assessments = []
        else:
            assessments = []

    return render(request, 'results/list_assessments.html', {
        'assessments': assessments, 
        'academic_class': academic_class
    })



#Grading System
@login_required
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
@login_required
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

@login_required
def assessment_list_view(request):
    assessments = Assessment.objects.all()
    context = {
        'assessments': assessments,
    }
    return render(request, 'results/assessment_list.html', context)

@login_required
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



@login_required
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

@login_required
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


def class_result_filter_view(request):
    years = AcademicYear.objects.all()
    terms = Term.objects.all()
    academic_class_streams = AcademicClassStream.objects.select_related(
        'academic_class', 'stream', 'academic_class__Class', 'academic_class__academic_year', 'academic_class__term'
    ).all()

    selected_year = request.GET.get('year_id')
    selected_term = request.GET.get('term_id')
    selected_class_stream = request.GET.get('class_stream_id')

    students = Student.objects.none()
    no_students_message = None

    if selected_year and selected_term and selected_class_stream:
        class_registers = ClassRegister.objects.filter(
            academic_class_stream_id=selected_class_stream
        )
        students = Student.objects.filter(id__in=class_registers.values('student_id')).order_by('student_name')

        if not students.exists():
            no_students_message = "No students found matching your criteria."

    context = {
        'years': years,
        'terms': terms,
        'academic_class_streams': academic_class_streams,
        'selected_year': selected_year,
        'selected_term': selected_term,
        'selected_class_stream': selected_class_stream,
        'students': students,
        'no_students_message': no_students_message,
    }
    return render(request, 'results/class_stream_filter.html', context)
def calculate_weighted_subject_averages(assessments):
    subject_scores = {}

    for result in assessments:
        subject = result.assessment.subject.name
        assessment_type = result.assessment.assessment_type
        weight = result.assessment.assessment_type.weight or 1
        raw_score = float(result.score)

        if subject not in subject_scores:
            subject_scores[subject] = {
                'total_score': 0,
                'total_weight': 0,
                'assessments': [],
                'teacher': getattr(result.assessment.subject, 'teacher', None),
                'points_total': 0,
                'count': 0,
            }

        subject_scores[subject]['total_score'] += raw_score * float(weight)
        subject_scores[subject]['total_weight'] += float(weight)
        subject_scores[subject]['points_total'] += float(result.points)
        subject_scores[subject]['count'] += 1

        subject_scores[subject]['assessments'].append({
            'id': assessment_type.id,
            'name': assessment_type.name
        })

    averages = []
    for subject, data in subject_scores.items():
        average = data['total_score'] / data['total_weight'] if data['total_weight'] else 0
        average_points = data['points_total'] / data['count'] if data['count'] else 0
        average_grade = get_grade_from_average(average)  # NEW: Add grade string from average

        unique_assessments = {a['id']: a for a in data['assessments']}.values()

        averages.append({
            'subject': subject,
            'average': average,
            'points': round(average_points, 2),
            'grade': average_grade,
            'assessments': list(unique_assessments),
            'teacher': data['teacher'],
        })

    return averages




@login_required
def student_performance_view(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    assessment_types = AssessmentType.objects.all()
    selected_assessment = request.GET.get("assessment_type")

    assessments = Result.objects.filter(student=student).select_related(
        'assessment__subject',
        'assessment__assessment_type'
    ).order_by('assessment__date')

    if selected_assessment:
        assessments = assessments.filter(assessment__assessment_type_id=selected_assessment)

    academic_class = AcademicClass.objects.filter(
        Class=student.current_class,
        academic_year=student.academic_year,
        term=student.term
    ).first()

    academic_class_stream = AcademicClassStream.objects.filter(
        academic_class=academic_class,
        stream=student.stream
    ).first() if academic_class else None

    performance_metrics = get_performance_metrics(assessments)
    subject_averages = calculate_weighted_subject_averages(assessments)

    subject_progress = {}
    for subject in set(r.assessment.subject.name for r in assessments):
        subject_scores = [(r.assessment.date, r.score) for r in assessments if r.assessment.subject.name == subject]
        subject_scores.sort(key=lambda x: x[0])
        progress = subject_scores[-1][1] - subject_scores[0][1] if len(subject_scores) > 1 else 0
        subject_progress[subject] = {
            'scores': subject_scores,
            'progress': progress,
            'trend': 'up' if progress > 0 else 'down' if progress < 0 else 'stable'
        }

    combined_subject_data = []
    for subject_avg in subject_averages:
        subject_name = subject_avg['subject']
        progress_data = subject_progress.get(subject_name, {'progress': 0, 'trend': 'stable', 'scores': []})
        combined_subject_data.append({
            **subject_avg,
            'progress': progress_data['progress'],
            'trend': progress_data['trend'],
            'scores': progress_data['scores'],
        })

    # Highest and Lowest Performing Subjects by average
    highest_subject = max(combined_subject_data, key=lambda s: s['average'], default=None)
    lowest_subject = min(combined_subject_data, key=lambda s: s['average'], default=None)

    performance_data = [
        {
            'score': float(performance_metrics['average']),
            'label': 'Overall Average Score',
            'icon': 'calculator',
            'type': 'avg',
            'subject': None
        },
        {
            'score': float(highest_subject['average']) if highest_subject else 0,
            'label': 'Best Performing Subject',
            'icon': 'trophy',
            'type': 'high',
            'subject': highest_subject['subject'] if highest_subject else 'N/A'
        },
        {
            'score': float(lowest_subject['average']) if lowest_subject else 0,
            'label': 'Lowest Performing Subject',
            'icon': 'exclamation-triangle',
            'type': 'low',
            'subject': lowest_subject['subject'] if lowest_subject else 'N/A'
        },
    ]

    assessment_data, assessment_dates = [], []
    grouped_assessments = {}
    for assessment in assessments:
        key = (assessment.assessment.date, assessment.assessment.assessment_type.name)
        grouped_assessments.setdefault(key, []).append(assessment)

    for (date, assessment_type), results in grouped_assessments.items():
        best_subject = max(results, key=lambda x: x.score)
        assessment_dates.append(date)
        assessment_data.append({
            'date': date,
            'type': assessment_type,
            'best_subject': {
                'name': best_subject.assessment.subject.name,
                'score': best_subject.score,
            },
            'subjects': {r.assessment.subject.name: r.score for r in results}
        })

    context = {
        "student": {
            "obj": student,
            "details": {
                "full_name": student.student_name,
                "registration_number": student.reg_no,
                "class_info": f"{student.current_class.name} {student.stream.stream}",
                "academic_year": student.academic_year,
                "birthdate": student.birthdate,
                "gender": student.get_gender_display(),
                "nationality": student.get_nationality_display(),
                "religion": student.get_religion_display(),
                "guardian": student.guardian,
                "relationship": student.relationship,
                "contact": student.contact,
                "email": getattr(student, 'email', 'N/A'),
                "address": student.address,
                "photo_url": student.photo.url if student.photo else '/static/images/default-student.jpg'
            }
        },
        "assessment_types": assessment_types,
        "assessments": performance_metrics['ordered_assessments'],
        "performance_data": performance_data,
        "subject_averages": combined_subject_data,
        "selected_assessment": selected_assessment,
        "assessment_data": assessment_data,
        "subject_progress": subject_progress,
    }

    return render(request, "results/student_performance.html", context)



@login_required
def student_assessment_type_report(request, student_id, assessment_type_id):
    student = get_object_or_404(Student, id=student_id)
    assessment_type = get_object_or_404(AssessmentType, id=assessment_type_id)

    results = Result.objects.filter(
        student=student,
        assessment__assessment_type=assessment_type
    ).select_related('assessment__subject')

    subject_scores = {}
    for result in results:
        subject = result.assessment.subject
        if subject.name not in subject_scores:
            subject_scores[subject.name] = {
                'scores': [],
                'total': 0,
                'count': 0
            }
        subject_scores[subject.name]['scores'].append(result)
        subject_scores[subject.name]['total'] += result.score
        subject_scores[subject.name]['count'] += 1

    # Calculate averages and grades
    summary = []
    for subject, data in subject_scores.items():
        avg = data['total'] / data['count']
        grade = result.grade  
        points = result.points
        summary.append({
            'subject': subject,
            'average': avg,
            'grade': grade,
            'points': points,
            'details': data['scores']
        })

    context = {
        'student': student,
        'assessment_type': assessment_type,
        'summary': summary,
    }

    return render(request, 'results/student_assessment_report.html', context)




@login_required
def student_term_report(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    results = Result.objects.filter(student=student).select_related(
        'assessment__subject', 'assessment__assessment_type'
    )

    subject_summary = {}

    for result in results:
        subject = result.assessment.subject.name
        if subject not in subject_summary:
            subject_summary[subject] = {
                'total': 0,
                'count': 0,
                'assessments': []
            }
        subject_summary[subject]['total'] += result.actual_score 
        subject_summary[subject]['count'] += 1
        subject_summary[subject]['assessments'].append(result)

    report_data = []
    for subject, data in subject_summary.items():
        avg = data['total'] / data['count'] if data['count'] else 0
        grade = data['assessments'][0].grade if data['assessments'] else "N/A"
        points = data['assessments'][0].points if data['assessments'] else 0
        report_data.append({
            'subject': subject,
            'average': avg,
            'grade': grade,
            'points': points,
            'details': data['assessments']
        })

    context = {
        'student': student,
        'report_data': report_data,
        'term': student.term,
        'academic_year': student.academic_year
    }

    return render(request, 'results/student_term_report.html', context)
