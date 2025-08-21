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
from app.selectors.results import get_grade_and_points, get_current_mode,get_performance_metrics, get_grade_from_average, calculate_weighted_subject_averages,get_division
from app.utils.pdf_utils import generate_student_report_pdf
from collections import defaultdict
import logging
logger = logging.getLogger(__name__)
from reportlab.lib.units import cm
from reportlab.lib import colors
from django.db.models import Case, When, Value, IntegerField
from django.db.models import Avg, Max
from app.selectors.school_settings import get_current_academic_year
from app.selectors.classes import get_current_term
from openpyxl import Workbook
from openpyxl.styles import Font, Border, Side, Alignment, PatternFill
from openpyxl.utils import get_column_letter
import io




@login_required
def add_results_view(request, assessment_id=None):
    if not assessment_id:
        return redirect('class_assessment_list')

    # Load the assessment and associated class
    assessment = get_object_or_404(Assessment, id=assessment_id)
    academic_class = assessment.academic_class

    # Get all registers for the class
    class_registers = ClassRegister.objects.filter(
        academic_class_stream__academic_class=academic_class
    ).select_related('student')  # Preload students to avoid extra DB hits

    students = []
    broken_registers = []

    # Safely collect only valid students
    for register in class_registers:
        try:
            students.append(register.student)
        except Student.DoesNotExist:
            broken_registers.append(register.id)
            continue

    if broken_registers:
        messages.warning(request, f"Some class register entries are broken (missing student data). Contact admin.")

    # Find existing results and determine who doesn't have one yet
    existing_results = Result.objects.filter(assessment=assessment)
    existing_student_ids = {result.student_id for result in existing_results}
    students_without_results = [s for s in students if s.id not in existing_student_ids]

    current_mode = ResultModeSetting.get_mode()

    # Handle form submission
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

    # Render the results form
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

@login_required
def class_result_filter_view(request):
    years = AcademicYear.objects.all()
    academic_class_streams = AcademicClassStream.objects.none()

    # Ensure user has a staff account
    staff_account = getattr(request.user, "staff_account", None)

    if staff_account:
        role_name = staff_account.role.name

        if role_name in ["Admin", "Head master", "Director of Studies"]:
            # Full access
            academic_class_streams = AcademicClassStream.objects.select_related(
                'academic_class', 'stream', 'academic_class__academic_year'
            ).all()
        
        elif role_name == "Class Teacher":
            # Restricted to streams assigned to them
            academic_class_streams = AcademicClassStream.objects.select_related(
                'academic_class', 'stream', 'academic_class__academic_year'
            ).filter(class_teacher=staff_account.staff)

        else:
            # e.g. Bursar, Support Staff → No class streams
            academic_class_streams = AcademicClassStream.objects.none()

    # Get selected parameters from GET request
    selected_year = request.GET.get('year_id')
    selected_class_stream = request.GET.get('class_stream_id')

    students = Student.objects.none()
    no_students_message = None

    if selected_year and selected_class_stream:
        class_registers = ClassRegister.objects.filter(
            academic_class_stream_id=selected_class_stream,
            academic_class_stream__academic_class__academic_year_id=selected_year
        )
        students = Student.objects.filter(id__in=class_registers.values('student_id')).order_by('student_name')

        if not students.exists():
            no_students_message = "No students found matching your criteria."

    context = {
        'years': years,
        'academic_class_streams': academic_class_streams,
        'selected_year': selected_year,
        'selected_class_stream': selected_class_stream,
        'students': students,
        'no_students_message': no_students_message,
    }
    return render(request, 'results/class_stream_filter.html', context)




@login_required
def student_performance_view(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    terms = Term.objects.filter(academic_year=student.academic_year)  
    assessment_types = AssessmentType.objects.all()  
    selected_term = request.GET.get("term_id")
    selected_assessment = request.GET.get("assessment_type")
    
    # Filter assessments by term and assessment type if selected
    assessments = Result.objects.filter(student=student).select_related(
        'assessment__subject',
        'assessment__assessment_type',
        'assessment__academic_class__term'
    ).order_by('assessment__date')
    
    if selected_term:
        assessments = assessments.filter(assessment__academic_class__term_id=selected_term)
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
        # Changed to use assessment_type.name instead of date
        subject_scores = [(r.assessment.assessment_type.name, r.score) for r in assessments if r.assessment.subject.name == subject]
        subject_scores.sort(key=lambda x: x[0])  # Sort by assessment_type name (alphabetically)
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
    
    # Get selected term and assessment type names for print view
    selected_term_name = Term.objects.filter(id=selected_term).first().term if selected_term else "All Terms"
    selected_assessment_name = AssessmentType.objects.filter(id=selected_assessment).first().name if selected_assessment else "All Assessment Types"
    
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
        "terms": terms,
        "assessment_types": assessment_types,
        "assessments": performance_metrics['ordered_assessments'],
        "performance_data": performance_data,
        "subject_averages": combined_subject_data,
        "selected_term": selected_term,
        "selected_term_name": selected_term_name,
        "selected_assessment": selected_assessment,
        "selected_assessment_name": selected_assessment_name,
        "assessment_data": assessment_data,
        "subject_progress": subject_progress,
    }
    
    return render(request, "results/student_performance.html", context)


@login_required
def student_assessment_type_report(request, student_id, assessment_type_id):
    student = get_object_or_404(Student, id=student_id)
    assessment_type = get_object_or_404(AssessmentType, id=assessment_type_id)
    school = SchoolSetting.load()
    
    # Get selected term or fallback to student's current term
    selected_term_id = request.GET.get('term_id', student.term.id if student.term else None)
    terms = Term.objects.filter(academic_year=student.academic_year) if student.academic_year else Term.objects.none()
    
    # Fetch results for the given student & assessment type
    results = Result.objects.filter(
        student=student,
        assessment__assessment_type=assessment_type
    ).select_related(
        'assessment__subject',
        'assessment__assessment_type',
        'assessment__academic_class__term'
    )
    if selected_term_id:
        results = results.filter(assessment__academic_class__term_id=selected_term_id)
    
    # Group scores by subject
    subject_scores = {}
    for result in results:
        subject = result.assessment.subject.name
        if subject not in subject_scores:
            subject_scores[subject] = {
                'scores': [],
                'total': Decimal('0.0'),
                'count': 0
            }
        subject_scores[subject]['scores'].append(result)
        subject_scores[subject]['total'] += Decimal(str(result.score))
        subject_scores[subject]['count'] += 1
    
    # Create summary list for each subject
    summary = []
    for subject, data in subject_scores.items():
        avg = (data['total'] / data['count']).quantize(Decimal('0.01')) if data['count'] else Decimal('0.00')
        grade, points = get_grade_and_points(avg)
        summary.append({
            'subject': subject,
            'average': float(avg),
            'grade': grade,
            'points': points,
            'details': data['scores']
        })
    
    # Calculate totals
    total_marks = sum(Decimal(str(result.score)) for result in results)  # Total marks scored
    total_aggregates = sum(item['points'] for item in summary)           # Sum of points across subjects
    overall_average = (total_marks / len(results)).quantize(Decimal('0.01')) if results else Decimal('0.00')
    overall_grade, overall_points = get_grade_and_points(overall_average)
    
    
    academic_year = student.academic_year.academic_year if student.academic_year else "-"
    term = Term.objects.filter(id=selected_term_id).first().term if selected_term_id else "-"
    
    context = {
        'school': school,
        'student': student,
        'assessment_type': assessment_type,
        'summary': summary,
        'term': term,
        'academic_year': academic_year,
        'total_marks': float(total_marks),
        'total_aggregates': total_aggregates,
        'overall_average': float(overall_average),
        'overall_grade': overall_grade,
        'overall_points': overall_points,
        'selected_term_id': selected_term_id,
        'terms': terms,
    }
    
    return render(request, 'results/student_assessment_report.html', context)

    
@login_required
def student_term_report(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    # Get all terms in the student's academic year
    terms = Term.objects.filter(
        academic_year=student.academic_year
    ).order_by('id')

    # Get selected term_id from query param or default
    selected_term_id = request.GET.get('term_id')
    if not selected_term_id:
        selected_term_id = (
            student.term.id if student.term
            else (terms.first().id if terms.exists() else None)
        )

    if not selected_term_id:
        messages.error(request, "No terms available for this student.")
        return redirect('student_performance_view', student_id=student_id)

    context = build_student_report_context(student, selected_term_id)

    
    context['terms'] = terms
    context['selected_term_id'] = str(selected_term_id)

    return render(request, 'results/student_term_report.html', context)

def build_student_report_context(student, term_id):
    school = SchoolSetting.load()
    academic_year = student.academic_year
    term = get_object_or_404(Term, id=term_id, academic_year=academic_year)

    # ---- Custom order definition for assessment types ----
    assessment_order = Case(
        When(name__iexact="BEGINNING OF TERM", then=Value(1)),
        When(name__iexact="MID OF TERM", then=Value(2)),
        When(name__iexact="END OF TERM INTERNAL", then=Value(3)),
        When(name__iexact="END OF TERM EXTERNAL", then=Value(4)),
        default=Value(5),
        output_field=IntegerField()
    )

    results_order = Case(
        When(assessment__assessment_type__name__iexact="BEGINNING OF TERM", then=Value(1)),
        When(assessment__assessment_type__name__iexact="MID OF TERM", then=Value(2)),
        When(assessment__assessment_type__name__iexact="END OF TERM INTERNAL", then=Value(3)),
        When(assessment__assessment_type__name__iexact="END OF TERM EXTERNAL", then=Value(4)),
        default=Value(5),
        output_field=IntegerField()
    )

    # Fetch assessment types in the desired order
    assessment_types = AssessmentType.objects.all().order_by(assessment_order, 'name')

    # Fetch results ordered by subject and custom assessment order
    results = Result.objects.filter(
        student=student,
        assessment__academic_class__term_id=term_id
    ).select_related(
        'assessment__subject',
        'assessment__assessment_type',
        'assessment__academic_class__term'
    ).order_by(
        'assessment__subject__name',
        results_order
    )

    # Prepare subject summaries and totals
    subject_summary = {}
    total_marks = Decimal('0.0')
    total_weight = Decimal('0.0')
    assessment_totals = {
        at.name: {'marks': Decimal('0.0'), 'points': Decimal('0.0'), 'count': 0}
        for at in assessment_types
    }

    for result in results:
        subject_name = result.assessment.subject.name or ''
        subject_desc = result.assessment.subject.description or ''
        subject_clean = (subject_name + " " + subject_desc).upper().replace(" ", "")
        exclude_from_totals = (
            'RELIGIOUSEDUCATION' in subject_clean or
            'READING' in subject_clean
        )

        assessment_type = result.assessment.assessment_type.name
        weight = Decimal(str(result.assessment.assessment_type.weight or 1))
        score = Decimal(str(result.score))

        if subject_name not in subject_summary:
            subject_summary[subject_name] = {
                'assessments': {},
                'total_score': Decimal('0.0'),
                'total_weight': Decimal('0.0')
            }

        grade, points = get_grade_and_points(score)
        subject_summary[subject_name]['assessments'][assessment_type] = {
            'score': float(score),
            'grade': grade,
            'points': points
        }
        subject_summary[subject_name]['total_score'] += score * weight
        subject_summary[subject_name]['total_weight'] += weight

        if not exclude_from_totals:
            total_marks += score * weight
            total_weight += weight

            if assessment_type in assessment_totals:
                assessment_totals[assessment_type]['marks'] += score
                assessment_totals[assessment_type]['points'] += Decimal(str(points))
                assessment_totals[assessment_type]['count'] += 1

    # Build report data per subject
    report_data = []
    for subject, data in subject_summary.items():
        avg = (
            data['total_score'] / data['total_weight']
        ).quantize(Decimal('0.01')) if data['total_weight'] else Decimal('0.00')
        grade, points = get_grade_and_points(avg)
        report_data.append({
            'subject': subject,
            'average': float(avg),
            'grade': grade,
            'points': points,
            'assessments': {
                at.name: data['assessments'].get(
                    at.name,
                    {'score': '-', 'grade': '-', 'points': '-'}
                )
                for at in assessment_types
            }
        })

    # Overall stats
    overall_average = (
        total_marks / total_weight
    ).quantize(Decimal('0.01')) if total_weight else Decimal('0.00')
    overall_grade, overall_points = get_grade_and_points(overall_average)

    # Calculate assessment divisions
    assessment_divisions = {}
    for at in assessment_types:
        total_points = int(assessment_totals[at.name]['points'])
        count = assessment_totals[at.name]['count']
        assessment_divisions[at.name] = (
            get_division(total_points) if count > 0 else "-"
        )

    total_aggregates = sum(
        assessment_totals[at.name]['points'] for at in assessment_types
        if assessment_totals[at.name]['count'] > 0
    )

    academic_year_str = student.academic_year.academic_year if student.academic_year else "-"
    term_name = term.term if term else "-"

    # --- Find next term ---
    next_term = None
    if term and student.academic_year:
        next_term = Term.objects.filter(
            academic_year=student.academic_year,
            start_date__gt=term.start_date
        ).order_by('start_date').first()

    next_term_start_date = next_term.start_date if next_term else None
    next_term_name = next_term.term if next_term else None

    colspan = 2 + len(assessment_types) + 1

    # ---- Signatures ----
    head_teacher_signature = Signature.objects.filter(position="HEAD TEACHER").first()
    
    # Get class teacher signature from AcademicClassStream model
    class_teacher_signature = None
    try:
        class_stream = AcademicClassStream.objects.get(
            academic_class=student.academic_class,
            stream=student.stream  # ⚠️ student must have a .stream
        )
        class_teacher_signature = class_stream.class_teacher_signature
    except (AcademicClassStream.DoesNotExist, AttributeError):
        class_teacher_signature = None

    return {
        'school': school,
        'student': student,
        'report_data': report_data,
        'assessment_types': assessment_types,
        'term': term_name,
        'academic_year': academic_year_str,
        'total_marks': float(total_marks),
        'overall_average': float(overall_average),
        'overall_grade': overall_grade,
        'overall_points': overall_points,
        'colspan': colspan,
        'assessment_totals': assessment_totals,
        'total_aggregates': int(total_aggregates),
        'assessment_divisions': assessment_divisions,
        'next_term_start_date': next_term_start_date,
        'next_term_name': next_term_name,
        'head_teacher_signature': head_teacher_signature,
        'class_teacher_signature': class_teacher_signature,  
    }


@login_required
def class_bulk_reports(request):
    academic_year_id = request.GET.get('academic_year_id')
    term_id = request.GET.get('term_id')
    class_id = request.GET.get('class_id')

    if not (academic_year_id and term_id and class_id):
        messages.error(request, "Please select Academic Year, Term, and Class first.")
        return redirect('class_performance_summary')

    academic_class = get_object_or_404(
        AcademicClass,
        academic_year_id=academic_year_id,
        term_id=term_id,
        Class_id=class_id
    )

    students = Student.objects.filter(current_class_id=class_id).order_by('student_name')
    school = SchoolSetting.load()
   

    reports = [build_student_report_context(student, term_id) for student in students]
    head_teacher_signature = Signature.objects.filter(position="HEAD TEACHER").first()

    context = {
        'school': school,
        'reports': reports,
        'class_obj': academic_class,
        'head_teacher_signature': head_teacher_signature,
    }
    return render(request, 'results/class_bulk_reports.html', context)

@login_required
def class_performance_summary(request):
    academic_year_id = request.GET.get('academic_year_id')
    term_id = request.GET.get('term_id')
    class_id = request.GET.get('class_id')
    assessment_type_id = request.GET.get('assessment_type_id')

    def to_int(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    academic_year_id = to_int(academic_year_id)
    term_id = to_int(term_id)
    class_id = to_int(class_id)
    assessment_type_id = to_int(assessment_type_id)

    academic_years = AcademicYear.objects.all()
    terms = Term.objects.all()
    classes = Class.objects.all()
    assessment_types = AssessmentType.objects.all()

    best_students = []
    subject_averages = []
    students_data = []
    subjects = []

    academic_class = None
    academic_class_exists = False

    if academic_year_id and term_id and class_id:
        try:
            academic_class = AcademicClass.objects.get(
                Class_id=class_id,
                academic_year_id=academic_year_id,
                term_id=term_id
            )
            academic_class_exists = True
        except AcademicClass.DoesNotExist:
            
            messages.warning(request, "No records found for the selected Academic Year, Term, and Class.")
            academic_class = None
            academic_class_exists = False

        if academic_class:
            results_qs = Result.objects.filter(assessment__academic_class=academic_class)
            if assessment_type_id:
                results_qs = results_qs.filter(assessment__assessment_type_id=assessment_type_id)

            # --- keep your best students + subject averages ---
            best_students = (
                results_qs
                .values('student__student_name', 'student__current_class__name')
                .annotate(average=Avg('score'))
                .order_by('-average')[:5]
            )
            subject_averages = (
                results_qs
                .values('assessment__subject__name')
                .annotate(avg_score=Avg('score'), best_score=Max('score'))
                .order_by('-avg_score')
            )

            # --- build assessment sheet ---
            subjects = Subject.objects.all().order_by('id')  
            students = Student.objects.filter(current_class_id=class_id)

            for student in students:
                results = {}
                total_marks = 0
                total_agg = 0

                for subject in subjects:
                    res = results_qs.filter(student=student, assessment__subject=subject).first()
                    if res:
                        results[subject.id] = {
                            'marks': res.score,
                            'agg': getattr(res, 'aggregate', '-'),
                        }
                        total_marks += res.score
                        total_agg += getattr(res, 'aggregate', 0)

                students_data.append({
                    'student': student,
                    'results': results,
                    'total_marks': total_marks,
                    'total_agg': total_agg,
                    'division': get_division(total_agg) if total_agg else '-'
                })

    context = {
        'academic_years': academic_years,
        'terms': terms,
        'classes': classes,
        'assessment_types': assessment_types,
        'best_students': best_students,
        'subject_averages': subject_averages,
        'students_data': students_data,
        'subjects': subjects,
        'selected_academic_year': str(academic_year_id) if academic_year_id else '',
        'selected_term': str(term_id) if term_id else '',
        'selected_class': str(class_id) if class_id else '',
        'selected_assessment_type': str(assessment_type_id) if assessment_type_id else '',
        'academic_class_exists': academic_class_exists,  # <-- flag for template
    }

    return render(request, 'results/class_performance_summary.html', context)




@login_required
def assessment_sheet_view(request):
    def q2(val, places="0.01"):
        return val.quantize(Decimal(places), rounding=ROUND_HALF_UP)

    def is_excluded_subject(name: str, desc: str = "") -> bool:
        text = f"{(name or '')} {(desc or '')}".upper().replace(" ", "")
        return "READING" in text or "RELIGIOUSEDUCATION" in text

    # Grades
    unique_grades = Class.objects.values_list("name", flat=True).distinct()
    selected_grade = request.GET.get("grade")
    if not selected_grade or selected_grade not in unique_grades:
        selected_grade = unique_grades.first() if unique_grades else None

    # Current year
    current_academic_year = AcademicYear.objects.filter(is_current=True).first()
    if not current_academic_year:
        messages.error(request, "No current academic year configured.")
        return redirect("student_performance_view")

    # Academic classes for the grade
    academic_classes = (
        AcademicClass.objects.filter(
            Class__name=selected_grade, academic_year=current_academic_year
        ).distinct()
        if selected_grade
        else AcademicClass.objects.none()
    )
    class_ids = academic_classes.values_list("id", flat=True)

    # Terms
    terms = Term.objects.filter(academic_year=current_academic_year).order_by("start_date")
    selected_term_id = request.GET.get("term_id")
    selected_assessment_type_id = request.GET.get("assessment_type_id")

    if not selected_term_id:
        selected_term = Term.objects.filter(
            academic_year=current_academic_year, is_current=True
        ).first()
        selected_term_id = (
            selected_term.id if selected_term else (terms.first().id if terms.exists() else None)
        )

    if not selected_term_id or not selected_grade:
        messages.error(request, "No valid grade or term available.")
        return redirect("student_performance_view")

    term_obj = get_object_or_404(Term, id=selected_term_id)
    assessment_type = (
        get_object_or_404(AssessmentType, id=selected_assessment_type_id)
        if selected_assessment_type_id
        else None
    )

    # Order assessment types
    assessment_order = Case(
        When(name__iexact="BEGINNING OF TERM", then=Value(1)),
        When(name__iexact="MID OF TERM", then=Value(2)),
        When(name__iexact="END OF TERM INTERNAL", then=Value(3)),
        When(name__iexact="END OF TERM EXTERNAL", then=Value(4)),
        default=Value(5),
        output_field=IntegerField(),
    )
    assessment_types = AssessmentType.objects.all().order_by(assessment_order, "name")

    # Registers
    class_registers = (
        ClassRegister.objects.filter(
            academic_class_stream__academic_class__id__in=class_ids,
            academic_class_stream__academic_class__term_id=selected_term_id,
        )
        .select_related("student", "academic_class_stream__academic_class")
        .order_by("student__student_name")
    )

    # Class teacher
    class_teacher = "Tr. [Teacher Name]"
    if academic_classes.exists():
        first_class_stream = AcademicClassStream.objects.filter(
            academic_class__id__in=class_ids,
            academic_class__term_id=selected_term_id,
        ).select_related("class_teacher").first()
        if first_class_stream and first_class_stream.class_teacher:
            class_teacher = f"{first_class_stream.class_teacher.first_name} {first_class_stream.class_teacher.last_name}"

    unique_subjects = []
    seen_subjects = set()
    students_data = []

    for register in class_registers:
        student = register.student
        results = Result.objects.filter(
            student=student,
            assessment__academic_class__term_id=selected_term_id,
        ).select_related("assessment__subject", "assessment__assessment_type")

        if assessment_type:
            results = results.filter(assessment__assessment_type=assessment_type)

        subj_stats = {}
        for r in results:
            subj_name = r.assessment.subject.name or ""
            subj_desc = r.assessment.subject.description or ""
            if subj_name not in seen_subjects:
                unique_subjects.append(subj_name)
                seen_subjects.add(subj_name)

            try:
                score = Decimal(str(r.score or 0))
            except Exception:
                score = Decimal("0")
            w = Decimal(str(r.assessment.assessment_type.weight or 1))

            if subj_name not in subj_stats:
                subj_stats[subj_name] = {"sum": Decimal("0"), "w": Decimal("0"), "desc": subj_desc}
            subj_stats[subj_name]["sum"] += score * w
            subj_stats[subj_name]["w"] += w

        subjects_payload = {}
        total_marks_sum = Decimal("0")
        total_aggregates_sum = 0

        for subj_name, stat in subj_stats.items():
            if stat["w"] > 0:
                avg = stat["sum"] / stat["w"]
            else:
                avg = Decimal("0")

            avg = q2(avg)
            grade, points = get_grade_and_points(float(avg))

            subjects_payload[subj_name] = {
                "score": int(avg),
                "agg": int(points),
            }

            if not is_excluded_subject(subj_name, stat["desc"]):
                total_marks_sum += avg
                total_aggregates_sum += int(points)

        student_record = {
            "name": student.student_name,
            "subjects": subjects_payload,
            "total_marks": int(q2(total_marks_sum)),
            "total_aggregates": total_aggregates_sum,
            "division": get_division(total_aggregates_sum) if total_aggregates_sum else "-",
        }
        students_data.append(student_record)

    # Handle Excel export
    if request.GET.get('export') == 'excel':
        wb = Workbook()
        ws = wb.active
        ws.title = f"{term_obj.term} Assessment"

        # Define styles
        bold_font = Font(name='Calibri', size=11, bold=True)
        regular_font = Font(name='Calibri', size=11)
        border = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin')
        )
        header_fill = PatternFill(start_color='F3F4F6', end_color='F3F4F6', fill_type='solid')
        center_align = Alignment(horizontal='center', vertical='center')
        left_align = Alignment(horizontal='left', vertical='center')

        # Metadata
        metadata = [
            ['School:', request.session.get('school_name', 'School Name')],
            ['Term:', term_obj.term],
            ['Grade:', selected_grade or 'N/A'],
            ['Class Teacher:', class_teacher],
            ['Assessment Type:', assessment_type.name if assessment_type else 'All Assessments'],
            [],
        ]
        for row_idx, (key, value) in enumerate(metadata, 1):
            ws.cell(row=row_idx, column=1).value = key
            ws.cell(row=row_idx, column=2).value = value
            ws.cell(row=row_idx, column=1).font = bold_font
            ws.cell(row=row_idx, column=2).font = regular_font
            ws.cell(row=row_idx, column=1).alignment = left_align
            ws.cell(row=row_idx, column=2).alignment = left_align

        # Headers
        header_row = len(metadata) + 1
        headers = ['No', 'Student Name'] + [f'{subj}' for subj in unique_subjects] + \
                  [f'{subj} AGG' for subj in unique_subjects] + ['Total Marks', 'Division']
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=header_row, column=col_idx)
            cell.value = header
            cell.font = bold_font
            cell.fill = header_fill
            cell.border = border
            cell.alignment = center_align

        # Data
        for row_idx, student in enumerate(students_data, header_row + 1):
            ws.cell(row=row_idx, column=1).value = row_idx - header_row
            ws.cell(row=row_idx, column=2).value = student['name'].title()
            col_idx = 3
            for subject in unique_subjects:
                ws.cell(row=row_idx, column=col_idx).value = student['subjects'].get(subject, {}).get('score', '-')
                ws.cell(row=row_idx, column=col_idx + 1).value = student['subjects'].get(subject, {}).get('agg', '-')
                col_idx += 2
            ws.cell(row=row_idx, column=col_idx).value = student['total_marks']
            ws.cell(row=row_idx, column=col_idx + 1).value = student['division']

            # Apply styles to data cells
            for c in range(1, len(headers) + 1):
                ws.cell(row=row_idx, column=c).font = regular_font
                ws.cell(row=row_idx, column=c).border = border
                ws.cell(row=row_idx, column=c).alignment = center_align

        # Adjust column widths
        ws.column_dimensions['A'].width = 10  # No
        ws.column_dimensions['B'].width = 30  # Student Name
        for col_idx, header in enumerate(headers[2:], 3):
            ws.column_dimensions[get_column_letter(col_idx)].width = 15

        # Set row heights
        for r in range(1, len(metadata)):
            ws.row_dimensions[r].height = 20
        ws.row_dimensions[header_row].height = 25
        for r in range(header_row + 1, ws.max_row + 1):
            ws.row_dimensions[r].height = 20

        # Save to buffer
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        # Create response
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{request.session.get("school_name", "School")}_{term_obj.term}_{selected_grade}_Assessment.xlsx"'
        response.write(buffer.getvalue())
        return response

    context = {
        "school_name": request.session.get('school_name', 'Bayan Learning Center'),
        "term": term_obj.term,
        "grade": selected_grade,
        "class_teacher": class_teacher,
        "students_data": students_data,
        "subjects": unique_subjects,
        "terms": terms,
        "selected_term_id": str(selected_term_id),
        "grades": unique_grades,
        "selected_grade": selected_grade,
        "assessment_types": assessment_types,
        "selected_assessment_type_id": selected_assessment_type_id,
    }
    return render(request, "results/assessment_sheet.html", context)