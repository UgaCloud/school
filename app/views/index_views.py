from django.shortcuts import render, redirect, HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q, F, ExpressionWrapper, DecimalField, Avg
from django.db.models.functions import TruncMonth
from django.core.cache import cache
from django.utils import timezone
from django.contrib import messages
from datetime import date
from app.models.classes import Class, AcademicClass, Term
from app.models.school_settings import AcademicYear
from app.models.staffs import Staff
from app.models.students import Student
from app.models.fees_payment import StudentBill, Payment
from app.models.finance import Budget, Expenditure, ExpenditureItem, IncomeSource, ApprovalWorkflow
from app.models.results import Assessment, Result, GradingSystem
from app.models.subjects import Subject
from app.models.communications import Announcement, Event
from app.models.attendance import AttendanceRecord, AttendanceStatus
from app.selectors.school_settings import get_current_academic_year


def under_construction_view(request):
    """Under construction / Coming soon page"""
    return render(request, "under_construction.html")


@login_required
def index_view(request):
    try:
        staff_account = request.user.staff_account
        session_role = request.session.get('active_role_name')
        if session_role:
            user_role = session_role
        else:
            user_role = staff_account.role.name
    except Exception:
        user_role = 'Support Staff'

    # Define role permissions
    head_roles = ['Head Teacher', 'Head master']
    admin_roles = ['Admin'] + head_roles
    finance_roles = ['Admin', 'Head Teacher', 'Head master', 'Bursar']
    academic_roles = ['Admin', 'Head Teacher', 'Head master', 'Director of Studies', 'Teacher', 'Class Teacher']
    teacher_roles = ['Admin', 'Head Teacher', 'Head master', 'Director of Studies', 'Teacher', 'Class Teacher']
    is_teacher_dashboard = user_role in ['Teacher', 'Class Teacher']
    is_head_dashboard = user_role in head_roles
    can_add_student = user_role in academic_roles and user_role not in ['Teacher']

    selected_term_param = (request.GET.get("term") or "").strip()
    term_options = []
    selected_term = None
    selected_term_label = ""

    # Basic staff statistics (visible to all except support staff)
    if user_role not in ['Support Staff']:
        total_staff = Staff.objects.count()
        total_males = Staff.objects.filter(gender='M').count()
        total_females = Staff.objects.filter(gender='F').count()
        male_percentage = (total_males / total_staff * 100) if total_staff > 0 else 0
        female_percentage = (total_females / total_staff * 100) if total_staff > 0 else 0
    else:
        total_staff = total_males = total_females = male_percentage = female_percentage = 0

    # Basic student statistics (visible to academic and admin roles)
    if user_role in academic_roles:
        total_students = Student.objects.filter(is_active=True).count()
        total_male_students = Student.objects.filter(gender='M', is_active=True).count()
        total_female_students = Student.objects.filter(gender='F', is_active=True).count()
        male_students_percentage = (total_male_students / total_students * 100) if total_students > 0 else 0
        female_students_percentage = (total_female_students / total_students * 100) if total_students > 0 else 0
    else:
        total_students = total_male_students = total_female_students = male_students_percentage = female_students_percentage = 0

    # Academic information (visible to academic and admin roles)
    # Also get current_year and current_term for finance roles since financial calculations depend on them
    if user_role in academic_roles or user_role in finance_roles:
        current_year = get_current_academic_year()
        current_term = Term.objects.filter(is_current=True).first()
        
        # Show a user-friendly message if no academic year is set
        if current_year is None:
            messages.error(request, "No academic year has been set. Please set an academic year to view this page.")
            return render(request, "index.html", {
                'user_role': user_role,
                'is_admin': user_role in admin_roles,
                'is_finance': user_role in finance_roles,
                'is_academic': user_role in academic_roles,
                'is_teacher': user_role in teacher_roles,
                'is_support': user_role == 'Support Staff',
            })
        term_options = list(Term.objects.filter(academic_year=current_year).order_by("term"))
        selected_term_ids = {str(term.id) for term in term_options}
        if selected_term_param in selected_term_ids:
            selected_term = next((term for term in term_options if str(term.id) == selected_term_param), None)
        elif current_term and current_term.academic_year_id == current_year.id:
            selected_term = current_term
        elif term_options:
            selected_term = term_options[0]
        else:
            selected_term = current_term

        if selected_term:
            selected_term_label = f"Term {selected_term.term} {selected_term.academic_year.academic_year}"
        current_term = selected_term
    else:
        current_year = current_term = None

    # Teacher-focused data (assigned classes/subjects + pending assessments)
    teacher_assignments = []
    teacher_subjects = []
    pending_assessments = []
    teacher_class_count = 0
    teacher_subject_count = 0
    pending_assessments_count = 0
    class_teacher_progress = []
    class_teacher_tasks = []
    class_teacher_birthdays = []
    class_streams = []
    if is_teacher_dashboard:
        from app.models.accounts import StaffAccount
        from app.models.classes import ClassSubjectAllocation, AcademicClassStream

        staff_account = StaffAccount.objects.filter(user=request.user).select_related("staff").first()
        if staff_account and staff_account.staff:
            teacher_assignments = list(
                ClassSubjectAllocation.objects.filter(subject_teacher=staff_account.staff)
                .select_related(
                    "academic_class_stream",
                    "academic_class_stream__academic_class",
                    "subject",
                )
                .order_by("academic_class_stream__academic_class__Class__name", "subject__name")
            )
            teacher_subjects = sorted({a.subject for a in teacher_assignments}, key=lambda s: s.name)
            teacher_class_count = len({a.academic_class_stream.academic_class_id for a in teacher_assignments})
            teacher_subject_count = len(teacher_subjects)

            # Pending assessments for assigned subjects/classes in current term/year
            if current_year and current_term:
                if user_role == "Class Teacher":
                    class_streams = list(
                        AcademicClassStream.objects.filter(class_teacher=staff_account.staff)
                        .select_related(
                            "academic_class__Class",
                            "stream"
                        )
                    )
                    class_ids = [cs.academic_class_id for cs in class_streams]
                    pending_assessments = list(
                        Assessment.objects.filter(
                            academic_class__academic_year=current_year,
                            academic_class__term=current_term,
                            academic_class_id__in=class_ids,
                        )
                        .select_related("academic_class", "assessment_type", "subject")
                        .order_by("-date")[:5]
                    )
                else:
                    subject_ids = [s.id for s in teacher_subjects]
                    class_ids = [a.academic_class_stream.academic_class_id for a in teacher_assignments]
                    pending_assessments = list(
                        Assessment.objects.filter(
                            academic_class__academic_year=current_year,
                            academic_class__term=current_term,
                            academic_class_id__in=class_ids,
                            subject_id__in=subject_ids,
                        )
                        .select_related("academic_class", "assessment_type", "subject")
                        .order_by("-date")[:5]
                    )
                pending_assessments_count = len(pending_assessments)

                today = timezone.localdate()
                if user_role == "Class Teacher":
                    class_teacher_birthdays = list(
                        Student.objects.filter(
                            is_active=True,
                            current_class_id__in=class_ids,
                            birthdate__month=today.month,
                            birthdate__day=today.day,
                        ).order_by("student_name")
                    )
                elif user_role == "Teacher":
                    class_teacher_birthdays = list(
                        Student.objects.filter(
                            is_active=True,
                            current_class_id__in=class_ids,
                            birthdate__month=today.month,
                            birthdate__day=today.day,
                        ).order_by("student_name")
                    )

                if user_role == "Class Teacher":
                    allocations = (
                        ClassSubjectAllocation.objects.filter(academic_class_stream__in=class_streams)
                        .select_related(
                            "subject",
                            "subject_teacher",
                            "academic_class_stream",
                            "academic_class_stream__academic_class",
                            "academic_class_stream__stream",
                        )
                    )
                    for allocation in allocations:
                        academic_class = allocation.academic_class_stream.academic_class
                        assessments = Assessment.objects.filter(
                            academic_class=academic_class,
                            subject=allocation.subject,
                            academic_class__academic_year=current_year,
                            academic_class__term=current_term,
                        ).select_related("result_batch")
                        results_qs = Result.objects.filter(assessment__in=assessments)
                        total_results = results_qs.count()
                        marked_results = results_qs.filter(status__in=["PENDING", "VERIFIED"]).count()
                        progress = round((marked_results / total_results) * 100, 1) if total_results else 0
                        batch_status = assessments.filter(result_batch__isnull=False).values_list("result_batch__status", flat=True).first() or "DRAFT"
                        submitted = batch_status in ["PENDING", "VERIFIED"]
                        pending_results = total_results - marked_results
                        if pending_results > 0 and batch_status == "VERIFIED":
                            batch_status = "PENDING"
                        class_teacher_progress.append({
                            "teacher": allocation.subject_teacher,
                            "subject": allocation.subject,
                            "class_name": academic_class.Class.name,
                            "stream": allocation.academic_class_stream.stream.stream,
                            "progress": progress,
                            "submitted": submitted,
                            "total": total_results,
                            "marked": marked_results,
                            "pending": pending_results,
                            "batch_status": batch_status,
                        })

                    unsubmitted_assessments = Assessment.objects.filter(
                        academic_class__academic_year=current_year,
                        academic_class__term=current_term,
                        academic_class_id__in=class_ids,
                    ).filter(Q(result_batch__status="DRAFT") | Q(result_batch__isnull=True)).count()
                    flagged_results_count = Result.objects.filter(
                        assessment__academic_class__academic_year=current_year,
                        assessment__academic_class__term=current_term,
                        assessment__academic_class_id__in=class_ids,
                        status="FLAGGED",
                    ).count()

                    class_id_for_links = class_ids[0] if class_ids else None
                    if pending_assessments_count and class_id_for_links:
                        class_teacher_tasks.append({
                            "label": f"{pending_assessments_count} assessments pending results",
                            "status": "Pending",
                            "url": reverse("list_assessments", args=[class_id_for_links]),
                        })
                    if unsubmitted_assessments and class_id_for_links:
                        class_teacher_tasks.append({
                            "label": f"{unsubmitted_assessments} assessments not submitted for verification",
                            "status": "Action",
                            "url": f"{reverse('list_assessments', args=[class_id_for_links])}?status=draft",
                        })
                    if flagged_results_count:
                        class_teacher_tasks.append({
                            "label": f"{flagged_results_count} results flagged – need correction",
                            "status": "Alert",
                            "url": reverse("class_assessment_list"),
                        })
        else:
            teacher_assignments = []
            teacher_subjects = []
            pending_assessments = []

    if user_role in academic_roles:
        # Class distribution (all academic roles)
        class_distribution = Student.objects.filter(is_active=True).values('current_class__name').annotate(
            count=Count('id')
        ).order_by('-count')[:15]
    else:
        class_distribution = []

    # Override class distribution for teacher dashboard (assigned classes only + gender counts)
    if is_teacher_dashboard and teacher_assignments:
        teacher_class_ids = list({a.academic_class_stream.academic_class_id for a in teacher_assignments})
        class_distribution = Student.objects.filter(
            is_active=True,
            current_class_id__in=teacher_class_ids
        ).values('current_class__name').annotate(
            count=Count('id'),
            male_count=Count('id', filter=Q(gender='M')),
            female_count=Count('id', filter=Q(gender='F'))
        ).order_by('-count')[:15]
    elif is_teacher_dashboard:
        class_distribution = []

    term_start_date = selected_term.start_date if selected_term else None
    term_end_date = selected_term.end_date if selected_term else None

    # Financial overview (visible to finance and admin roles)
    if user_role in finance_roles and current_year and current_term:
        total_fees_collected = Payment.objects.filter(
            bill__academic_class__academic_year=current_year,
            bill__academic_class__term=current_term,
            payment_date__range=(term_start_date, term_end_date),
        ).aggregate(total=Sum('amount'))['total'] or 0

        total_fees_outstanding = StudentBill.objects.filter(
            academic_class__academic_year=current_year,
            academic_class__term=current_term,
            status='Unpaid',
        ).aggregate(total=Sum('items__amount'))['total'] or 0

        # Budget information
        current_budget = Budget.objects.filter(
            academic_year=current_year,
            term=current_term
        ).first() if current_year and current_term else None

        budget_allocated = current_budget.budget_total if current_budget else 0

        # Calculate budget spent including VAT by summing ExpenditureItem amounts and VAT
        if current_budget:
            expenditures = Expenditure.objects.filter(
                budget_item__budget=current_budget
            ).prefetch_related('items')
            budget_spent = 0
            for exp in expenditures:
                items_total = sum(item.amount for item in exp.items.all())
                budget_spent += items_total + exp.vat
        else:
            budget_spent = 0
    else:
        total_fees_collected = total_fees_outstanding = budget_allocated = budget_spent = 0
        current_budget = None

    if user_role in finance_roles and term_start_date and term_end_date:
        recent_payments = Payment.objects.filter(
            payment_date__range=(term_start_date, term_end_date),
        ).select_related('bill__student').order_by('-payment_date')[:5]
        recent_expenditures = Expenditure.objects.filter(
            date_incurred__range=(term_start_date, term_end_date)
        ).order_by('-date_incurred')[:5]
        pending_approvals = ApprovalWorkflow.objects.filter(status='pending').select_related('expenditure')[:5]
    else:
        recent_payments = []
        recent_expenditures = []
        pending_approvals = []

    if user_role in academic_roles:
        recent_registrations = Student.objects.filter(
            academic_year=current_year
        ).order_by('-id')[:5] if current_year else []
    else:
        recent_registrations = []

    # Dashboard communications
    now = timezone.now()
    if user_role in {"Admin", "Head Teacher", "Head master"}:
        audience = None
    elif user_role == "Director of Studies":
        audience = ["all", "dos"]
    elif user_role == "Bursar":
        audience = ["all", "bursar"]
    elif user_role == "Class Teacher":
        audience = ["all", "class_teacher", "teachers"]
    elif user_role == "Teacher":
        audience = ["all", "teachers"]
    else:
        audience = ["all"]

    dashboard_announcements = Announcement.objects.filter(
        is_active=True,
        starts_at__lte=now,
    ).filter(Q(ends_at__isnull=True) | Q(ends_at__gte=now))
    dashboard_events = Event.objects.filter(
        is_active=True,
        start_datetime__gte=now
    ).order_by("start_datetime")

    if audience is not None:
        dashboard_announcements = dashboard_announcements.filter(audience__in=audience)
        dashboard_events = dashboard_events.filter(audience__in=audience)

    dashboard_announcements = dashboard_announcements[:5]
    dashboard_events = dashboard_events[:5]

    # Performance metrics - visible to academic and admin roles
    total_assessments = 0
    completed_assessments = 0
    if user_role in academic_roles and current_year:
        # Scope assessment metrics to the current term
        total_assessments = Assessment.objects.filter(
            academic_class__academic_year=current_year,
            academic_class__term=current_term
        ).count()

        completed_assessments = Result.objects.filter(
            assessment__academic_class__academic_year=current_year,
            assessment__academic_class__term=current_term
        ).values('assessment').distinct().count()

        assessment_completion_rate = (completed_assessments / total_assessments * 100) if total_assessments > 0 else 0
    else:
        assessment_completion_rate = 0

    # Quick stats for charts - only for roles that can see the data
    monthly_enrollment = [
        {'month': 1, 'count': 0},
        {'month': 2, 'count': 0},
        {'month': 3, 'count': 0},
        {'month': 4, 'count': 0},
        {'month': 5, 'count': 0},
        {'month': 6, 'count': 0},
        {'month': 7, 'count': 0},
        {'month': 8, 'count': 0},
        {'month': 9, 'count': 0},
        {'month': 10, 'count': 0},
        {'month': 11, 'count': 0},
        {'month': 12, 'count': 0}
    ]

    # Gender distribution data for charts - role-based
    if user_role not in ['Support Staff']:
        staff_gender_data = [
            {'label': 'Male Staff', 'value': total_males, 'color': '#3498db'},
            {'label': 'Female Staff', 'value': total_females, 'color': '#e74c3c'}
        ]
    else:
        staff_gender_data = []

    if user_role in academic_roles:
        student_gender_data = [
            {'label': 'Male Students', 'value': total_male_students, 'color': '#f39c12'},
            {'label': 'Female Students', 'value': total_female_students, 'color': '#9b59b6'}
        ]
    else:
        student_gender_data = []

    # Fee collection status - only for finance roles
    if user_role in finance_roles and current_year and current_term:
        paid_bills = StudentBill.objects.filter(
            academic_class__academic_year=current_year,
            academic_class__term=current_term,
            status='Paid',
        ).count()

        unpaid_bills = StudentBill.objects.filter(
            academic_class__academic_year=current_year,
            academic_class__term=current_term,
            status='Unpaid',
        ).count()

        overdue_bills = StudentBill.objects.filter(
            academic_class__academic_year=current_year,
            academic_class__term=current_term,
            status='Overdue',
        ).count()

        total_bills = paid_bills + unpaid_bills + overdue_bills

        # Calculate fee collection rate based on amount collected vs amount billed
        total_billed = StudentBill.objects.filter(
            academic_class__academic_year=current_year,
            academic_class__term=current_term,
        ).aggregate(total=Sum('items__amount'))['total'] or 0

        fee_collection_rate = (total_fees_collected / total_billed * 100) if total_billed > 0 else 0
    else:
        paid_bills = unpaid_bills = overdue_bills = total_bills = fee_collection_rate = 0

    # Calculate role-aware metrics
    if user_role in academic_roles and current_year:
        # Count only classes in the current term to avoid double-counting across terms
        active_classes = AcademicClass.objects.filter(
            academic_year=current_year,
            term=current_term
        ).count()
    else:
        active_classes = 0

    total_subjects = Subject.objects.count() if user_role in academic_roles else 0
    pending_tasks = unpaid_bills + overdue_bills if user_role in finance_roles else 0

    # Chart data
    class_performance_labels = []
    class_performance_values = []
    class_readiness_labels = []
    class_readiness_values = []
    class_assessment_totals = []
    class_assessment_completed = []
    subject_performance_labels = []
    subject_performance_values = []
    top_classes = []
    bottom_classes = []
    top_subjects = []
    bottom_subjects = []
    performance_trend_labels = []
    performance_trend_values = []
    grade_distribution_labels = []
    grade_distribution_values = []
    grade_distribution_colors = []
    enrollment_trend_labels = []
    enrollment_trend_active_values = []
    enrollment_trend_inactive_values = []
    attendance_heatmap_series = []
    class_results_distribution_labels = []
    class_results_distribution_series = []
    fees_collection_labels = []
    fees_collection_expected = []
    fees_collection_collected = []
    fees_trend_labels = []
    fees_trend_values = []
    expenses_labels = []
    expenses_values = []
    result_status_percent = 0

    total_results = 0
    verified_results = 0
    if user_role in academic_roles and current_year and current_term:
        analytics_cache_key = f"dashboard:analytics:v1:{current_year.id}:{current_term.id}"
        cached_analytics = cache.get(analytics_cache_key)
        if cached_analytics:
            class_performance_labels = cached_analytics["class_performance_labels"]
            class_performance_values = cached_analytics["class_performance_values"]
            class_readiness_labels = cached_analytics["class_readiness_labels"]
            class_readiness_values = cached_analytics["class_readiness_values"]
            class_assessment_totals = cached_analytics["class_assessment_totals"]
            class_assessment_completed = cached_analytics["class_assessment_completed"]
            subject_performance_labels = cached_analytics["subject_performance_labels"]
            subject_performance_values = cached_analytics["subject_performance_values"]
            top_classes = cached_analytics["top_classes"]
            bottom_classes = cached_analytics["bottom_classes"]
            top_subjects = cached_analytics["top_subjects"]
            bottom_subjects = cached_analytics["bottom_subjects"]
            performance_trend_labels = cached_analytics["performance_trend_labels"]
            performance_trend_values = cached_analytics["performance_trend_values"]
            grade_distribution_labels = cached_analytics["grade_distribution_labels"]
            grade_distribution_values = cached_analytics["grade_distribution_values"]
            grade_distribution_colors = cached_analytics["grade_distribution_colors"]
            enrollment_trend_labels = cached_analytics["enrollment_trend_labels"]
            enrollment_trend_active_values = cached_analytics["enrollment_trend_active_values"]
            enrollment_trend_inactive_values = cached_analytics["enrollment_trend_inactive_values"]
            attendance_heatmap_series = cached_analytics["attendance_heatmap_series"]
            class_results_distribution_labels = cached_analytics["class_results_distribution_labels"]
            class_results_distribution_series = cached_analytics["class_results_distribution_series"]
            total_results = cached_analytics["total_results"]
            verified_results = cached_analytics["verified_results"]
            result_status_percent = cached_analytics["result_status_percent"]
        else:
            term_academic_classes = list(
                AcademicClass.objects.filter(
                    academic_year=current_year,
                    term=current_term,
                ).select_related("Class")
            )
            for academic_class in term_academic_classes:
                total_class_assessments = Assessment.objects.filter(academic_class=academic_class).count()
                completed_class_assessments = (
                    Result.objects.filter(assessment__academic_class=academic_class)
                    .values("assessment")
                    .distinct()
                    .count()
                )
                readiness_percent = round(
                    (completed_class_assessments / total_class_assessments) * 100, 1
                ) if total_class_assessments else 0
                class_readiness_labels.append(academic_class.Class.name)
                class_readiness_values.append(readiness_percent)
                class_assessment_totals.append(total_class_assessments)
                class_assessment_completed.append(completed_class_assessments)

            class_perf = (
                Result.objects.filter(assessment__academic_class__academic_year=current_year,
                                      assessment__academic_class__term=current_term)
                .values("assessment__academic_class__Class__name")
                .annotate(avg_score=Avg("score"))
                .order_by("assessment__academic_class__Class__name")
            )
            class_perf_list = list(class_perf)
            class_performance_labels = [c["assessment__academic_class__Class__name"] for c in class_perf_list]
            class_performance_values = [round(c["avg_score"] or 0, 1) for c in class_perf_list]
            class_perf_sorted = sorted(class_perf_list, key=lambda x: (x["avg_score"] or 0), reverse=True)
            top_classes = class_perf_sorted[:5]
            bottom_classes = list(reversed(class_perf_sorted[-5:])) if class_perf_sorted else []

            subject_perf = (
                Result.objects.filter(assessment__academic_class__academic_year=current_year,
                                      assessment__academic_class__term=current_term)
                .values("assessment__subject__name")
                .annotate(avg_score=Avg("score"))
                .order_by("assessment__subject__name")
            )
            subject_perf_list = list(subject_perf)
            subject_performance_labels = [s["assessment__subject__name"] for s in subject_perf_list]
            subject_performance_values = [round(s["avg_score"] or 0, 1) for s in subject_perf_list]
            subject_perf_sorted = sorted(subject_perf_list, key=lambda x: (x["avg_score"] or 0), reverse=True)
            top_subjects = subject_perf_sorted[:5]
            bottom_subjects = list(reversed(subject_perf_sorted[-5:])) if subject_perf_sorted else []

            trend_perf = (
                Result.objects.filter(assessment__academic_class__academic_year=current_year)
                .values("assessment__academic_class__term__term")
                .annotate(avg_score=Avg("score"))
                .order_by("assessment__academic_class__term__term")
            )
            performance_trend_labels = [t["assessment__academic_class__term__term"] for t in trend_perf]
            performance_trend_values = [round(t["avg_score"] or 0, 1) for t in trend_perf]

            grading = list(GradingSystem.objects.all().order_by("min_score"))
            grade_distribution_labels = [g.grade for g in grading]
            if not grade_distribution_labels:
                grade_distribution_labels = ["Ungraded"]
            grade_counts = {grade: 0 for grade in grade_distribution_labels}
            for row in Result.objects.filter(assessment__academic_class__academic_year=current_year,
                                             assessment__academic_class__term=current_term).values("score"):
                score = row["score"]
                grade = None
                for g in grading:
                    if g.min_score <= score <= g.max_score:
                        grade = g.grade
                        break
                if grade is None:
                    grade = "Ungraded"
                if grade not in grade_counts:
                    grade_counts[grade] = 0
                    grade_distribution_labels.append(grade)
                grade_counts[grade] += 1
            grade_distribution_values = [grade_counts.get(k, 0) for k in grade_distribution_labels]
            color_palette = ["#d9534f", "#f0ad4e", "#ffd45a", "#5cb85c", "#337ab7", "#6f42c1", "#d63384", "#8b5a2b", "#2c3e50"]
            grade_distribution_colors = [color_palette[i % len(color_palette)] for i in range(len(grade_distribution_labels))]

            enrollment_stats = (
                Student.objects.filter(academic_year=current_year)
                .values("term__term")
                .annotate(
                    active_count=Count("id", filter=Q(is_active=True)),
                    inactive_count=Count("id", filter=Q(is_active=False)),
                )
                .order_by("term__term")
            )
            enrollment_trend_labels = [f"Term {row['term__term']}" for row in enrollment_stats]
            enrollment_trend_active_values = [row["active_count"] for row in enrollment_stats]
            enrollment_trend_inactive_values = [row["inactive_count"] for row in enrollment_stats]

            attendance_daily = (
                AttendanceRecord.objects.filter(
                    session__academic_year=current_year,
                    session__term=current_term,
                )
                .values("session__date")
                .annotate(
                    total=Count("id"),
                    present_like=Count("id", filter=Q(status__in=[AttendanceStatus.PRESENT, AttendanceStatus.LATE])),
                )
                .order_by("session__date")
            )
            heatmap_points = []
            for row in attendance_daily:
                total = row["total"] or 0
                present_like = row["present_like"] or 0
                rate = round((present_like / total) * 100, 1) if total else 0
                heatmap_points.append({
                    "x": row["session__date"].strftime("%b %d"),
                    "y": rate,
                })
            attendance_heatmap_series = [{"name": "Attendance %", "data": heatmap_points}]

            class_names = []
            class_grade_totals = {}
            grade_order = list(grade_distribution_labels)
            result_rows = Result.objects.filter(
                assessment__academic_class__academic_year=current_year,
                assessment__academic_class__term=current_term,
            ).values("assessment__academic_class__Class__name", "score")
            for row in result_rows:
                class_name = row["assessment__academic_class__Class__name"] or "Unknown"
                if class_name not in class_grade_totals:
                    class_grade_totals[class_name] = {grade: 0 for grade in grade_order}
                    class_names.append(class_name)
                score = row["score"]
                assigned_grade = "Ungraded"
                for g in grading:
                    if g.min_score <= score <= g.max_score:
                        assigned_grade = g.grade
                        break
                if assigned_grade not in class_grade_totals[class_name]:
                    class_grade_totals[class_name][assigned_grade] = 0
                    if assigned_grade not in grade_order:
                        grade_order.append(assigned_grade)
                class_grade_totals[class_name][assigned_grade] += 1

            class_results_distribution_labels = class_names
            class_results_distribution_series = [
                {
                    "name": grade,
                    "data": [class_grade_totals[class_name].get(grade, 0) for class_name in class_names],
                }
                for grade in grade_order
            ]

            total_results = Result.objects.filter(
                assessment__academic_class__academic_year=current_year,
                assessment__academic_class__term=current_term,
            ).count()
            verified_results = Result.objects.filter(
                assessment__academic_class__academic_year=current_year,
                assessment__academic_class__term=current_term,
                status="VERIFIED",
            ).count()
            result_status_percent = round((verified_results / total_results) * 100, 1) if total_results else 0

            cache.set(analytics_cache_key, {
                "class_performance_labels": class_performance_labels,
                "class_performance_values": class_performance_values,
                "class_readiness_labels": class_readiness_labels,
                "class_readiness_values": class_readiness_values,
                "class_assessment_totals": class_assessment_totals,
                "class_assessment_completed": class_assessment_completed,
                "subject_performance_labels": subject_performance_labels,
                "subject_performance_values": subject_performance_values,
                "top_classes": top_classes,
                "bottom_classes": bottom_classes,
                "top_subjects": top_subjects,
                "bottom_subjects": bottom_subjects,
                "performance_trend_labels": performance_trend_labels,
                "performance_trend_values": performance_trend_values,
                "grade_distribution_labels": grade_distribution_labels,
                "grade_distribution_values": grade_distribution_values,
                "grade_distribution_colors": grade_distribution_colors,
                "enrollment_trend_labels": enrollment_trend_labels,
                "enrollment_trend_active_values": enrollment_trend_active_values,
                "enrollment_trend_inactive_values": enrollment_trend_inactive_values,
                "attendance_heatmap_series": attendance_heatmap_series,
                "class_results_distribution_labels": class_results_distribution_labels,
                "class_results_distribution_series": class_results_distribution_series,
                "total_results": total_results,
                "verified_results": verified_results,
                "result_status_percent": result_status_percent,
            }, 300)

    # Action queue for admin/head roles
    action_queue = []
    if user_role in admin_roles:
        classes_without_streams = 0
        if current_year and current_term:
            classes_without_streams = AcademicClass.objects.filter(
                academic_year=current_year,
                term=current_term,
            ).annotate(stream_count=Count("class_streams")).filter(stream_count=0).count()

        pending_results_count = max(total_assessments - completed_assessments, 0)
        unverified_results_count = max(total_results - verified_results, 0)

        action_queue = [
            {
                "label": "Academic classes missing streams",
                "count": classes_without_streams,
                "severity": "high" if classes_without_streams else "ok",
                "url": reverse("academic_class_page"),
            },
            {
                "label": "Assessments pending results",
                "count": pending_results_count,
                "severity": "medium" if pending_results_count else "ok",
                "url": reverse("class_assessment_list"),
            },
            {
                "label": "Unverified results",
                "count": unverified_results_count,
                "severity": "medium" if unverified_results_count else "ok",
                "url": reverse("verification_overview"),
            },
            {
                "label": "Overdue fee bills",
                "count": overdue_bills if user_role in finance_roles else 0,
                "severity": "high" if (overdue_bills if user_role in finance_roles else 0) else "ok",
                "url": reverse("fees_status"),
            },
        ]
        action_queue = [item for item in action_queue if item["count"] > 0]
    action_queue_total = sum(item["count"] for item in action_queue)

    if user_role in finance_roles and current_year and current_term and term_start_date and term_end_date:
        expected_fees = StudentBill.objects.filter(
            academic_class__academic_year=current_year,
            academic_class__term=current_term,
        ).aggregate(total=Sum("items__amount"))["total"] or 0
        collected_fees = total_fees_collected
        fees_collection_labels = [selected_term_label]
        fees_collection_expected = [float(expected_fees)]
        fees_collection_collected = [float(collected_fees)]

        daily_collections = (
            Payment.objects.filter(
                bill__academic_class__academic_year=current_year,
                bill__academic_class__term=current_term,
                payment_date__range=(term_start_date, term_end_date),
            )
            .annotate(bucket=TruncMonth("payment_date"))
            .values("bucket")
            .annotate(total=Sum("amount"))
            .order_by("bucket")
        )
        collections_by_month = {
            date(item["bucket"].year, item["bucket"].month, 1): float(item["total"] or 0)
            for item in daily_collections if item["bucket"]
        }
        month_cursor = date(term_start_date.year, term_start_date.month, 1)
        month_end = date(term_end_date.year, term_end_date.month, 1)
        while month_cursor <= month_end:
            fees_trend_labels.append(month_cursor.strftime("%b"))
            fees_trend_values.append(collections_by_month.get(month_cursor, 0))
            if month_cursor.month == 12:
                month_cursor = date(month_cursor.year + 1, 1, 1)
            else:
                month_cursor = date(month_cursor.year, month_cursor.month + 1, 1)

        expense_breakdown = (
            ExpenditureItem.objects.filter(
                expenditure__date_incurred__range=(term_start_date, term_end_date),
            ).values("item_name")
            .annotate(total=Sum(ExpressionWrapper(F("quantity") * F("unit_cost"), output_field=DecimalField())))
            .order_by("-total")[:5]
        )
        expenses_labels = [e["item_name"] for e in expense_breakdown]
        expenses_values = [float(e["total"] or 0) for e in expense_breakdown]

    context = {
        # User role for template conditionals
        'user_role': user_role,
        'is_admin': user_role in admin_roles,
        'is_finance': user_role in finance_roles,
        'is_academic': user_role in academic_roles,
        'is_teacher': user_role in teacher_roles,
        'is_support': user_role == 'Support Staff',
        'is_teacher_dashboard': is_teacher_dashboard,
        'is_head_dashboard': is_head_dashboard,
        'can_add_student': can_add_student,
        'recent_expenditures': recent_expenditures,
        'pending_approvals': pending_approvals,
        'dashboard_announcements': dashboard_announcements,
        'dashboard_events': dashboard_events,

        # Basic statistics
        'total_staff': total_staff,
        'total_males': total_males,
        'total_females': total_females,
        'total_students': total_students,
        'total_male_students': total_male_students,
        'total_female_students': total_female_students,
        'male_percentage': round(male_percentage, 2),
        'female_percentage': round(female_percentage, 2),
        'male_students_percentage': round(male_students_percentage, 2),
        'female_students_percentage': round(female_students_percentage, 2),

        # Academic information
        'current_year': current_year,
        'current_term': current_term,
        'class_distribution': class_distribution,

        # Teacher dashboard data
        'teacher_assignments': teacher_assignments,
        'teacher_subjects': teacher_subjects,
        'teacher_class_count': teacher_class_count,
        'teacher_subject_count': teacher_subject_count,
        'pending_assessments': pending_assessments,
        'pending_assessments_count': pending_assessments_count,
        'class_teacher_progress': class_teacher_progress,
        'class_teacher_tasks': class_teacher_tasks,
        'class_teacher_birthdays': class_teacher_birthdays,
        'class_streams': class_streams,

        # Financial data
        'total_fees_collected': total_fees_collected,
        'total_fees_outstanding': total_fees_outstanding,
        'budget_allocated': budget_allocated,
        'budget_spent': budget_spent,
        'budget_remaining': budget_allocated - budget_spent,
        'selected_term': str(current_term.id) if current_term else "",
        'selected_term_label': selected_term_label,
        'term_options': term_options,

        # Recent activities
        'recent_payments': recent_payments,
        'recent_registrations': recent_registrations,

        # Performance metrics
        'assessment_completion_rate': round(assessment_completion_rate, 1),
        'fee_collection_rate': round(fee_collection_rate, 1),

        # Chart data
        'staff_gender_data': staff_gender_data,
        'student_gender_data': student_gender_data,
        'monthly_enrollment': list(monthly_enrollment),

        # Additional metrics
        'paid_bills': paid_bills,
        'unpaid_bills': unpaid_bills,
        'overdue_bills': overdue_bills,
        'total_bills': total_bills,

        # Charts
        'class_performance_labels': class_performance_labels,
        'class_performance_values': class_performance_values,
        'class_readiness_labels': class_readiness_labels,
        'class_readiness_values': class_readiness_values,
        'class_assessment_totals': class_assessment_totals,
        'class_assessment_completed': class_assessment_completed,
        'subject_performance_labels': subject_performance_labels,
        'subject_performance_values': subject_performance_values,
        'top_classes': top_classes,
        'bottom_classes': bottom_classes,
        'top_subjects': top_subjects,
        'bottom_subjects': bottom_subjects,
        'performance_trend_labels': performance_trend_labels,
        'performance_trend_values': performance_trend_values,
        'grade_distribution_labels': grade_distribution_labels,
        'grade_distribution_values': grade_distribution_values,
        'grade_distribution_colors': grade_distribution_colors,
        'enrollment_trend_labels': enrollment_trend_labels,
        'enrollment_trend_active_values': enrollment_trend_active_values,
        'enrollment_trend_inactive_values': enrollment_trend_inactive_values,
        'attendance_heatmap_series': attendance_heatmap_series,
        'class_results_distribution_labels': class_results_distribution_labels,
        'class_results_distribution_series': class_results_distribution_series,
        'fees_collection_labels': fees_collection_labels,
        'fees_collection_expected': fees_collection_expected,
        'fees_collection_collected': fees_collection_collected,
        'fees_trend_labels': fees_trend_labels,
        'fees_trend_values': fees_trend_values,
        'expenses_labels': expenses_labels,
        'expenses_values': expenses_values,
        'result_status_percent': result_status_percent,
        'dashboard_chart_data': {
            'class_performance_labels': class_performance_labels,
            'class_performance_values': class_performance_values,
            'class_readiness_labels': class_readiness_labels,
            'class_readiness_values': class_readiness_values,
            'class_assessment_totals': class_assessment_totals,
            'class_assessment_completed': class_assessment_completed,
            'subject_performance_labels': subject_performance_labels,
            'subject_performance_values': subject_performance_values,
            'top_classes': top_classes,
            'bottom_classes': bottom_classes,
            'top_subjects': top_subjects,
            'bottom_subjects': bottom_subjects,
            'performance_trend_labels': performance_trend_labels,
            'performance_trend_values': performance_trend_values,
            'grade_distribution_labels': grade_distribution_labels,
            'grade_distribution_values': grade_distribution_values,
            'grade_distribution_colors': grade_distribution_colors,
            'enrollment_trend_labels': enrollment_trend_labels,
            'enrollment_trend_active_values': enrollment_trend_active_values,
            'enrollment_trend_inactive_values': enrollment_trend_inactive_values,
            'attendance_heatmap_series': attendance_heatmap_series,
            'class_results_distribution_labels': class_results_distribution_labels,
            'class_results_distribution_series': class_results_distribution_series,
            'fees_collection_labels': fees_collection_labels,
            'fees_collection_expected': fees_collection_expected,
            'fees_collection_collected': fees_collection_collected,
            'fees_trend_labels': fees_trend_labels,
            'fees_trend_values': fees_trend_values,
            'expenses_labels': expenses_labels,
            'expenses_values': expenses_values,
            'result_status_percent': result_status_percent,
        },

        # Quick actions data
        'pending_tasks': pending_tasks,
        'active_classes': active_classes,
        'total_subjects': total_subjects,
        'action_queue': action_queue,
        'action_queue_total': action_queue_total,
        'has_performance_data': bool(top_classes or bottom_classes or top_subjects or bottom_subjects),
        'has_class_readiness_data': bool(class_readiness_labels),
        'has_enrollment_trend_data': bool(enrollment_trend_labels),
        'has_attendance_heatmap_data': bool(attendance_heatmap_series and attendance_heatmap_series[0].get("data")),
        'has_class_results_distribution_data': bool(class_results_distribution_labels and class_results_distribution_series),
        'has_finance_chart_data': bool(fees_collection_expected or fees_trend_values or expenses_values),
    }

    return render(request, "index.html", context)
