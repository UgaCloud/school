from django.shortcuts import render, redirect, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q, F, ExpressionWrapper, DecimalField
from django.utils import timezone
from django.contrib import messages
from datetime import datetime, timedelta
from app.models.classes import Class, AcademicClass, Term
from app.models.school_settings import AcademicYear
from app.models.staffs import Staff
from app.models.students import Student
from app.models.fees_payment import StudentBill, Payment
from app.models.finance import Budget, Expenditure, ExpenditureItem, IncomeSource
from app.models.results import Assessment, Result
from app.selectors.school_settings import get_current_academic_year


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
    admin_roles = ['Admin', 'Head Teacher']
    finance_roles = ['Admin', 'Head Teacher', 'Bursar']
    academic_roles = ['Admin', 'Head Teacher', 'Director of Studies', 'Teacher', 'Class Teacher']
    teacher_roles = ['Admin', 'Head Teacher', 'Director of Studies', 'Teacher', 'Class Teacher']

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
    else:
        current_year = current_term = None

    if user_role in academic_roles:
        # Class distribution
        class_distribution = Student.objects.filter(is_active=True).values('current_class__name').annotate(
            count=Count('id')
        ).order_by('-count')[:15]
    else:
        class_distribution = []

    # Financial overview (visible to finance and admin roles)
    if user_role in finance_roles:
        # Filter by both academic year AND current term to match financial summary report
        total_fees_collected = Payment.objects.filter(
            bill__academic_class__academic_year=current_year,
            bill__academic_class__term=current_term
        ).aggregate(total=Sum('amount'))['total'] or 0

        total_fees_outstanding = StudentBill.objects.filter(
            academic_class__academic_year=current_year,
            academic_class__term=current_term,
            status='Unpaid'
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

    # Recent activities (last 7 days) - role-based visibility
    seven_days_ago = timezone.now() - timedelta(days=7)

    if user_role in finance_roles:
        recent_payments = Payment.objects.filter(
            payment_date__gte=seven_days_ago
        ).select_related('bill__student').order_by('-payment_date')[:5]
    else:
        recent_payments = []

    if user_role in academic_roles:
        recent_registrations = Student.objects.filter(
            academic_year=current_year
        ).order_by('-id')[:5] if current_year else []
    else:
        recent_registrations = []

    # Performance metrics - visible to academic and admin roles
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
    if user_role in finance_roles and current_year:
        paid_bills = StudentBill.objects.filter(
            academic_class__academic_year=current_year,
            academic_class__term=current_term,
            status='Paid'
        ).count()

        unpaid_bills = StudentBill.objects.filter(
            academic_class__academic_year=current_year,
            academic_class__term=current_term,
            status='Unpaid'
        ).count()

        overdue_bills = StudentBill.objects.filter(
            academic_class__academic_year=current_year,
            academic_class__term=current_term,
            status='Overdue'
        ).count()

        total_bills = paid_bills + unpaid_bills + overdue_bills

        # Calculate fee collection rate based on amount collected vs amount billed
        total_billed = StudentBill.objects.filter(
            academic_class__academic_year=current_year,
            academic_class__term=current_term
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

    total_subjects = Class.objects.count() if user_role in academic_roles else 0
    pending_tasks = unpaid_bills + overdue_bills if user_role in finance_roles else 0

    context = {
        # User role for template conditionals
        'user_role': user_role,
        'is_admin': user_role in admin_roles,
        'is_finance': user_role in finance_roles,
        'is_academic': user_role in academic_roles,
        'is_teacher': user_role in teacher_roles,
        'is_support': user_role == 'Support Staff',

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

        # Financial data
        'total_fees_collected': total_fees_collected,
        'total_fees_outstanding': total_fees_outstanding,
        'budget_allocated': budget_allocated,
        'budget_spent': budget_spent,
        'budget_remaining': budget_allocated - budget_spent,

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

        # Quick actions data
        'pending_tasks': pending_tasks,
        'active_classes': active_classes,
        'total_subjects': total_subjects,
    }

    return render(request, "index.html", context)
