from django.shortcuts import render, redirect, HttpResponseRedirect, HttpResponse, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from django.template.loader import render_to_string
import csv
from django.db import IntegrityError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from app.constants import *
import app.selectors.students as student_selectors
import app.forms.student as student_forms
from app.services.students import register_student, bulk_student_registration, delete_all_csv_files
from app.selectors.model_selectors import *
from app.forms.student import StudentForm
from app.models.students import Student, StudentDocument
import app.forms.student as student_forms
import app.selectors.students as student_selectors
import app.selectors.classes as class_selectors
from app.selectors.classes import *
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from app.models import ClassRegister
from django.db.models import Q
from app.models import (
    ClassRegister,
    AcademicClassStream,
    AcademicClass,
    Class,
    Stream,
    Section,
    Staff,
)
from app.services.level_scope import (
    bind_form_level_querysets,
    get_level_classes_queryset,
    get_level_class_streams_queryset,
    get_level_sections_queryset,
    get_level_students_queryset,
)
from app.services.school_level import get_active_school_level



@login_required
def manage_student_view(request):
    active_level = get_active_school_level(request)
    staff_account = getattr(request.user, "staff_account", None)
    role_name = staff_account.role.name if staff_account and staff_account.role else None
    active_role = request.session.get("active_role_name")
    is_class_teacher = (role_name == "Class Teacher" or active_role == "Class Teacher")
    status = request.GET.get("status", "active")
    page_number = request.GET.get("page", 1)
    try:
        per_page = int(request.GET.get("per_page", 25))
    except (TypeError, ValueError):
        per_page = 25

    scoped_students = get_level_students_queryset(active_level=active_level).select_related("current_class", "stream")
    if is_class_teacher and staff_account and staff_account.staff:
        class_streams = get_level_class_streams_queryset(active_level=active_level).filter(
            class_teacher=staff_account.staff
        )
        class_stream_ids = class_streams.values_list("id", flat=True)
        base_students_qs = scoped_students.filter(
            classregister__academic_class_stream_id__in=class_stream_ids
        ).distinct()
    elif is_class_teacher:
        base_students_qs = scoped_students.none()
    else:
        base_students_qs = scoped_students

    total_all = base_students_qs.count()
    total_active = base_students_qs.filter(is_active=True).count()
    total_inactive = base_students_qs.filter(is_active=False).count()

    if status == "inactive":
        students_list = base_students_qs.filter(is_active=False)
    elif status == "all":
        students_list = base_students_qs
    else:
        students_list = base_students_qs.filter(is_active=True)
    
    # Paginate the students
    paginator = Paginator(students_list, per_page)
    
    try:
        students = paginator.page(page_number)
    except PageNotAnInteger:
        students = paginator.page(1)
    except EmptyPage:
        students = paginator.page(paginator.num_pages)
    
    student_form = student_forms.StudentForm()
    bind_form_level_querysets(student_form, active_level=active_level)
    csv_form = student_forms.StudentRegistrationCSVForm()
    current_academic_year = get_current_academic_year()
    try:
        current_term = get_current_term()
    except Exception:
        current_term = None
    
    context = {
        "students": students,
        "student_form": student_form,
        "csv_form": csv_form,
        "status": status,
        "total_active": total_active,
        "total_inactive": total_inactive,
        "total_all": total_all,
        "per_page": per_page,
        "current_academic_year": current_academic_year,
        "current_term": current_term,
        "quick_sections": get_level_sections_queryset(active_level=active_level),
        "quick_teachers": Staff.objects.filter(is_academic_staff=True).order_by("first_name", "last_name"),
    }
    
    return render(request, "student/manage_students.html", context)


@login_required
def quick_create_academic_class_view(request):
    if request.method != "POST":
        return HttpResponseRedirect(reverse("student_page"))

    active_level = get_active_school_level(request)
    current_academic_year = get_current_academic_year()
    if not current_academic_year:
        messages.error(request, "No current academic year is configured.")
        return HttpResponseRedirect(reverse("settings_page"))

    try:
        current_term = get_current_term()
    except Exception:
        messages.error(request, "No current term is configured.")
        return HttpResponseRedirect(reverse("academic_class_page"))

    class_id = request.POST.get("quick_selected_class_id") or request.POST.get("quick_class_id")
    section_id = request.POST.get("quick_section_id")
    fees_amount = request.POST.get("quick_fees_amount")

    if not (class_id and section_id and fees_amount):
        messages.error(request, "Class, section and fees amount are required.")
        return HttpResponseRedirect(reverse("student_page"))

    try:
        class_obj = get_level_classes_queryset(active_level=active_level).get(id=class_id)
        section_obj = get_level_sections_queryset(active_level=active_level).get(id=section_id)
        fees_value = int(fees_amount)
    except (Class.DoesNotExist, Section.DoesNotExist, ValueError):
        messages.error(request, "Invalid academic class setup values.")
        return HttpResponseRedirect(reverse("student_page"))

    if class_obj.section_id != section_obj.id:
        messages.error(request, "Selected section does not match the class section.")
        return HttpResponseRedirect(reverse("student_page"))

    academic_class, created = AcademicClass.objects.get_or_create(
        Class=class_obj,
        academic_year=current_academic_year,
        term=current_term,
        defaults={"section": section_obj, "fees_amount": fees_value},
    )
    if not created:
        updated = False
        if academic_class.section_id != section_obj.id:
            academic_class.section = section_obj
            updated = True
        if academic_class.fees_amount != fees_value:
            academic_class.fees_amount = fees_value
            updated = True
        if updated:
            academic_class.save(update_fields=["section", "fees_amount"])
            messages.success(request, "Academic Class existed and was updated.")
        else:
            messages.info(request, "Academic Class already exists.")
    else:
        messages.success(request, "Academic Class created successfully.")
    return HttpResponseRedirect(reverse("student_page"))


@login_required
def quick_create_class_stream_view(request):
    if request.method != "POST":
        return HttpResponseRedirect(reverse("student_page"))

    active_level = get_active_school_level(request)
    current_academic_year = get_current_academic_year()
    if not current_academic_year:
        messages.error(request, "No current academic year is configured.")
        return HttpResponseRedirect(reverse("settings_page"))

    try:
        current_term = get_current_term()
    except Exception:
        messages.error(request, "No current term is configured.")
        return HttpResponseRedirect(reverse("academic_class_page"))

    class_id = request.POST.get("quick_selected_class_id") or request.POST.get("quick_stream_class_id")
    stream_id = request.POST.get("quick_selected_stream_id") or request.POST.get("quick_stream_id")
    teacher_id = request.POST.get("quick_teacher_id")

    if not (class_id and stream_id and teacher_id):
        messages.error(request, "Class, stream and class teacher are required.")
        return HttpResponseRedirect(reverse("student_page"))

    try:
        class_obj = get_level_classes_queryset(active_level=active_level).get(id=class_id)
        stream_obj = Stream.objects.get(id=stream_id)
        teacher_obj = Staff.objects.get(id=teacher_id)
    except (Class.DoesNotExist, Stream.DoesNotExist, Staff.DoesNotExist):
        messages.error(request, "Invalid class stream setup values.")
        return HttpResponseRedirect(reverse("student_page"))

    if not teacher_obj.is_academic_staff:
        messages.error(request, "Selected class teacher must be marked as academic staff.")
        return HttpResponseRedirect(reverse("student_page"))

    academic_class = AcademicClass.objects.filter(
        Class=class_obj,
        academic_year=current_academic_year,
        term=current_term,
    ).first()
    if not academic_class:
        messages.error(
            request,
            "Academic Class does not exist yet for the selected class in current year/term. "
            "Create it first in Quick Setup.",
        )
        return HttpResponseRedirect(reverse("student_page"))

    class_stream, created = AcademicClassStream.objects.get_or_create(
        academic_class=academic_class,
        stream=stream_obj,
        defaults={"class_teacher": teacher_obj},
    )
    if not created and class_stream.class_teacher_id != teacher_obj.id:
        class_stream.class_teacher = teacher_obj
        class_stream.save(update_fields=["class_teacher"])
        messages.success(request, "Class stream existed and class teacher was updated.")
    elif created:
        messages.success(request, "Class stream created successfully.")
    else:
        messages.info(request, "Class stream already exists.")
    return HttpResponseRedirect(reverse("student_page"))


@login_required
def add_student_view(request):
    active_level = get_active_school_level(request)
    if request.method == "POST":
        student_form = student_forms.StudentForm(request.POST, request.FILES)
        bind_form_level_querysets(student_form, active_level=active_level)

        if student_form.is_valid():
            _class = student_form.cleaned_data.get("current_class")
            stream = student_form.cleaned_data.get("stream")

            current_academic_year = get_current_academic_year()
            if not current_academic_year:
                messages.error(
                    request,
                    "No current academic year is configured. Configure it under School Settings first.",
                )
                return HttpResponseRedirect(reverse("settings_page"))

            try:
                term = get_current_term()
            except Exception:
                messages.error(
                    request,
                    "No current term is configured. Set one term as current under Academics.",
                )
                return HttpResponseRedirect(reverse("academic_class_page"))

            academic_class = AcademicClass.objects.filter(
                academic_year=current_academic_year,
                Class=_class,
                term=term,
            ).first()

            if not academic_class:
                messages.error(
                    request,
                    f"Missing Academic Class setup for {_class} in {current_academic_year} / {term}. "
                    "Create it in Academic Classes first.",
                )
                return HttpResponseRedirect(reverse("academic_class_page"))

            class_stream_exists = AcademicClassStream.objects.filter(
                academic_class=academic_class, stream=stream
            ).exists()

            if not class_stream_exists:
                messages.error(
                    request,
                    f"Missing class stream '{stream}' for {_class}. Add it on the Academic Class details page.",
                )
                return HttpResponseRedirect(
                    reverse("academic_class_details_page", args=[academic_class.id])
                )

            student = student_form.save()
            register_student(student, _class, stream)
            messages.success(request, SUCCESS_ADD_MESSAGE)

        else:
            messages.error(request, FAILURE_MESSAGE)

    return HttpResponseRedirect(reverse(manage_student_view))


def _get_scoped_student_or_404(request, student_id):
    active_level = get_active_school_level(request)
    return get_object_or_404(get_level_students_queryset(active_level=active_level), pk=student_id)


@login_required
def student_details_view(request, id):
    student = _get_scoped_student_or_404(request, id)
    
    # Fetch exam reports 
    from app.models.results import Result
    from app.models import AcademicYear, Term, AssessmentType
    
    academic_year_id = request.GET.get('academic_year')
    term_id = request.GET.get('term')
    assessment_type_id = request.GET.get('assessment_type')
    

    exam_reports = Result.objects.filter(student=student).select_related(
        'assessment__subject',
        'assessment__assessment_type',
        'assessment__academic_class__term',
        'assessment__academic_class__academic_year'
    ).order_by('-assessment__date')

    if academic_year_id:
        exam_reports = exam_reports.filter(assessment__academic_class__academic_year_id=academic_year_id)
    if term_id:
        exam_reports = exam_reports.filter(assessment__academic_class__term_id=term_id)
    if assessment_type_id:
        exam_reports = exam_reports.filter(assessment__assessment_type_id=assessment_type_id)
    
    from django.db.models import Q
    
    academic_years = AcademicYear.objects.filter(
        id__in=Result.objects.filter(student=student).values('assessment__academic_class__academic_year')
    ).distinct().order_by('-academic_year')
    
    # Get terms
    terms = Term.objects.filter(
        id__in=Result.objects.filter(student=student).values('assessment__academic_class__term')
    ).distinct().order_by('term')
    
    # Get assessment types
    assessment_types = AssessmentType.objects.filter(
        id__in=Result.objects.filter(student=student).values('assessment__assessment_type')
    ).distinct().order_by('name')
    
    # Performance analysis
    from django.db.models import Avg
    overall_avg = exam_reports.aggregate(avg=Avg('score'))['avg'] or 0
    assessment_performance = exam_reports.values('assessment__assessment_type__name').annotate(avg_score=Avg('score')).order_by('assessment__assessment_type__name')
    subject_performance = exam_reports.values('assessment__subject__name').annotate(avg_score=Avg('score')).order_by('assessment__subject__name')

    context = {
        "student": student,
        "general_documents": student.documents.filter(bill__isnull=True),
        "bill_documents": student.documents.filter(bill__isnull=False),
        "document_type_choices": DOCUMENT_TYPES,
        "exam_reports": exam_reports,
        "academic_years": academic_years,
        "terms": terms,
        "assessment_types": assessment_types,
        "selected_academic_year": academic_year_id,
        "selected_term": term_id,
        "selected_assessment_type": assessment_type_id,
        "active_tab": request.GET.get('tab') or ("exam" if (academic_year_id or term_id or assessment_type_id) else "docs"),
        "assessment_performance": assessment_performance,
        "subject_performance": subject_performance,
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
        ['Reg No', 'Student Name', 'Gender', 'Birth Date (YYYY-MM-DD)', 'Nationality', 'Religion', 'Address',
         'Guardian', 'Relationship', 'Guardian Contact', 'Academic Year', 'Current Class', 'Stream', 'Term (1/2/3)'])

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
                import_result = bulk_student_registration(csv_object)
                created_count = import_result.get("created_count", 0)
                skipped_count = import_result.get("skipped_count", 0)
                errors = import_result.get("errors", [])

                if created_count:
                    messages.success(request, f"Successfully imported {created_count} student(s).")
                if skipped_count:
                    messages.warning(
                        request,
                        f"Skipped {skipped_count} row(s). First issue: {errors[0] if errors else 'Unknown error.'}"
                    )
            except ValueError as e:
                messages.error(request, str(e))  
            except IntegrityError:
                messages.error(request, INTEGRITY_ERROR_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)

    return HttpResponseRedirect(reverse(manage_student_view))

@login_required
def edit_student_view(request, id):
    active_level = get_active_school_level(request)
    student = _get_scoped_student_or_404(request, id)
    is_modal = request.GET.get("modal") == "1" or request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == 'POST':
        student_form = StudentForm(request.POST, request.FILES, instance=student)
        bind_form_level_querysets(student_form, active_level=active_level)
        if student_form.is_valid():
            student_form.save()
            messages.success(request, SUCCESS_EDIT_MESSAGE)
            if is_modal:
                return JsonResponse({"ok": True, "message": SUCCESS_EDIT_MESSAGE})
            return redirect(add_student_view)
        else:
            if is_modal:
                html = render_to_string(
                    "student/partials/edit_student_form.html",
                    {"form": student_form, "student": student},
                    request=request,
                )
                return JsonResponse({"ok": False, "html": html}, status=400)
            messages.error(request, FAILURE_MESSAGE)
    else:
        student_form = StudentForm(instance=student)
        bind_form_level_querysets(student_form, active_level=active_level)

    context = {
        "form": student_form,
        "student": student,
        "is_modal": is_modal,
    }
    if is_modal:
        return render(request, "student/partials/edit_student_form.html", context)

    return render(request, "student/edit_student.html", context)

@login_required
def delete_student_view(request, id):
    student = _get_scoped_student_or_404(request, id)

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
    active_level = get_active_school_level(request)
    # Filter active students not yet registered
    registered_students = ClassRegister.objects.values_list('student_id', flat=True)
    unregistered_students = get_level_students_queryset(active_level=active_level).filter(
        is_active=True
    ).exclude(id__in=registered_students)

    if request.method == "POST":
        selected_students = request.POST.getlist("students")

        # Register selected students
        for student_id in selected_students:
            student = get_object_or_404(
                get_level_students_queryset(active_level=active_level),
                id=student_id,
            )

            # Fetch the AcademicClassStream instance
            try:
                academic_class_stream = get_level_class_streams_queryset(active_level=active_level).get(
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


@login_required
def upload_student_document(request, id):
    student = _get_scoped_student_or_404(request, id)

    if request.method == "POST":
        document_type = request.POST.get('document_type')
        file = request.FILES.get('file')

        if document_type and file:
            StudentDocument.objects.create(
                student=student,
                document_type=document_type,
                file=file
            )
            messages.success(request, "Document uploaded successfully!")
        else:
            messages.error(request, "Please provide both document type and file.")

    return redirect('student_details_page', id=student.id)


@login_required
def delete_student_document(request, id):
    document = get_object_or_404(StudentDocument, id=id)
    student = _get_scoped_student_or_404(request, document.student_id)
    student_id = student.id
    document.delete()
    messages.success(request, "Document deleted successfully.")
    return redirect('student_details_page', id=student_id)


@login_required
def download_student_exam_report(request, id):
    from app.models.results import Result
    from app.utils.pdf_utils import generate_student_report_pdf
    from django.http import HttpResponse
    
    student = _get_scoped_student_or_404(request, id)
    exam_reports = Result.objects.filter(student=student).select_related(
        'assessment__subject',
        'assessment__assessment_type',
        'assessment__academic_class__term'
    ).order_by('-assessment__date')
    
    # Generate PDF
    pdf_buffer = generate_student_report_pdf(student, exam_reports)
    
    # Create HTTP response with PDF
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{student.student_name}_Exam_Report.pdf"'
    return response


@login_required
def view_student_exam_report(request, id):
    from app.models.results import Result
    from app.utils.pdf_utils import generate_student_report_pdf
    from django.http import HttpResponse
    
    student = _get_scoped_student_or_404(request, id)
    exam_reports = Result.objects.filter(student=student).select_related(
        'assessment__subject',
        'assessment__assessment_type',
        'assessment__academic_class__term'
    ).order_by('-assessment__date')
    
    # Generate PDF
    pdf_buffer = generate_student_report_pdf(student, exam_reports)
    
    # Create HTTP response with PDF for inline viewing
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{student.student_name}_Exam_Report.pdf"'
    return response
