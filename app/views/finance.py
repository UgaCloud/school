from django.shortcuts import render, HttpResponsePermanentRedirect,redirect
from django.urls import reverse
from django.contrib import messages
from app.constants import *
from app.models.finance import *
from app.models.fees_payment import *
from app.forms.finance import *
from app.models.classes import *
from app.models.school_settings import *
from app.selectors.model_selectors import *
import app.forms.finance as finance_forms
import app.selectors.finance as finance_selector
from django.http import HttpResponse
import csv
from django.utils.dateparse import parse_date
from django.contrib.auth.decorators import login_required

@login_required
def manage_income_sources(request):
    form = finance_forms.IncomeSourceForm()
    income_sources = get_all_model_records(IncomeSource)
    
    context = {
        "income_sources": income_sources,
        "form": form
    }
    return render(request, "finance/income_sources.html", context)

@login_required
def add_income_source(request):
    if request.method == "POST":
        form = finance_forms.IncomeSourceForm(request.POST)
        
        if form.is_valid():
            form.save()
            
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
    
    return HttpResponsePermanentRedirect(reverse(manage_income_sources))


@login_required
def edit_income_sources(request, id):
    income_source = get_model_record(IncomeSource,id)
    if request.method =="POST":
        form = finance_forms.IncomeSourceForm(request.POST, instance=income_source)
        if form.is_valid():
            form.save()
            messages.success(request, SUCCESS_ADD_MESSAGE)
            return HttpResponsePermanentRedirect(reverse(manage_income_sources))
        else:
            messages.error(request, FAILURE_MESSAGE)
  
    form = finance_forms.IncomeSourceForm(instance=income_source)
    context={
        "form": form,
        "income_source":income_source
    }
    return render(request,"finance/edit_income_sources.html",context)
    
     

def delete_income_source(request, id):
    income_source = get_model_record(IncomeSource, id)
    
    income_source.delete()
    messages.success(request, DELETE_MESSAGE)
    
    return HttpResponsePermanentRedirect(reverse(manage_income_sources))

@login_required
def manage_expenses(request):
    form = finance_forms.ExpenseForm()
    expenses = get_all_model_records(Expense)
    edit_forms = {expense.id: finance_forms.ExpenseForm(instance=expense) for expense in expenses}
    
    context = {
        "expenses": expenses,
        "form": form,
        "edit_forms": edit_forms
    }
    return render(request, "finance/expenses.html", context)

@login_required
def add_expense(request):
    if request.method == "POST":
        form = finance_forms.ExpenseForm(request.POST)
        
        if form.is_valid():
            form.save()
            
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
    
    return HttpResponsePermanentRedirect(reverse(manage_expenses))


@login_required
def edit_expenses(request, id):
    expense = get_model_record(Expense, id)
    
    if request.method == 'POST':
        form = finance_forms.ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, SUCCESS_ADD_MESSAGE)
            return redirect(manage_expenses)  
        else:
            messages.error(request, FAILURE_MESSAGE)
  
    form = finance_forms.ExpenseForm(instance=expense)
    context = {
        'form': form,
        'expense': expense,
        
    }
    
    return render(request, 'finance/edit_expense.html', context)


def delete_expense(request, id):
    expense = get_model_record(Expense, id)
    
    expense.delete()
    messages.success(request, DELETE_MESSAGE)
    
    return HttpResponsePermanentRedirect(reverse(manage_expenses))

@login_required
def manage_expenditures(request):
    form = finance_forms.ExpenditureForm()
    # Optional server-side filters without altering data
    start_date = request.GET.get('start_date') or ''
    end_date = request.GET.get('end_date') or ''
    expenditures_qs = Expenditure.objects.all().order_by('-date_incurred', '-id')
    if start_date:
        expenditures_qs = expenditures_qs.filter(date_incurred__gte=start_date)
    if end_date:
        expenditures_qs = expenditures_qs.filter(date_incurred__lte=end_date)

    expenditures = expenditures_qs
    edit_forms = {expenditure.id: finance_forms.ExpenditureForm(instance=expenditure) for expenditure in expenditures}
    
    context = {
        "expenditures": expenditures,
        "form": form,
        "edit_forms": edit_forms,
        "start_date": start_date,
        "end_date": end_date
    }
    return render(request, "finance/expenditures.html", context)

@login_required
def add_expenditure(request):
    if request.method == "POST":
        form = finance_forms.ExpenditureForm(request.POST, request.FILES)
        if form.is_valid():
            expenditure = form.save()
            messages.success(request, SUCCESS_ADD_MESSAGE)
            return HttpResponsePermanentRedirect(reverse(manage_expenditure_items, args=[expenditure.id]))
        else:
            messages.error(request, FAILURE_MESSAGE)
            return HttpResponsePermanentRedirect(reverse(manage_expenditures))
    return HttpResponsePermanentRedirect(reverse(manage_expenditures))

@login_required
def edit_expenditures(request, id):
    expenditure = get_model_record(Expenditure, id)
    
    if request.method == 'POST':
        form = ExpenditureForm(request.POST, request.FILES, instance=expenditure)
        
        if form.is_valid():
            form.save()
            messages.success(request, SUCCESS_ADD_MESSAGE)
            return redirect(reverse(manage_expenditures))
        else:
            messages.error(request, FAILURE_MESSAGE)
    else:
        form = ExpenditureForm(instance=expenditure)

    # Inline HTML rendering
    return render(request, 'finance/edit_expenditure.html', {'form': form})

@login_required
def delete_expenditure(request, id):
    expenditure = get_model_record(Expenditure, id)
    
    expenditure.delete()
    messages.success(request, DELETE_MESSAGE)
    
    return HttpResponsePermanentRedirect(reverse(manage_expenditures))

@login_required
def manage_expenditure_items(request, id):
    expenditure = get_model_record(Expenditure, id)
    form = finance_forms.ExpenditureItemForm(initial={"expenditure":expenditure})
    expenditure_items = finance_selector.get_expenditure_items(expenditure)
    
    context = {
        "expenditure_items": expenditure_items,
        "form": form,
        "expenditure": expenditure
    }
    return render(request, "finance/expenditure_items.html", context)

@login_required
def add_expenditure_item(request):
    if request.method == "POST":
        form = finance_forms.ExpenditureItemForm(request.POST)
        expenditure_id = request.POST["expenditure"]
        if form.is_valid():
            form.save()
            
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
    
    return HttpResponsePermanentRedirect(reverse(manage_expenditure_items, args=[expenditure_id]))

@login_required
def edit_expenditure_items(request, id):
    expenditure_item = get_model_record(ExpenditureItem, id)
    if request.method == "POST":
        form = finance_forms.ExpenditureItemForm(request.POST, instance=expenditure_item)
        if form.is_valid():
            form.save()
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)

        
        expenditure_id = expenditure_item.expenditure.id  
        return HttpResponsePermanentRedirect(reverse(manage_expenditure_items, args=[expenditure_id]))

    form = finance_forms.ExpenditureItemForm(instance=expenditure_item)
    context = {
        "form": form,
        "expenditure_item": expenditure_item
    }
    return render(request, "finance/edit_expenditure_item.html", context)

    

def delete_expenditure_item(request, id):
    expenditure_item = get_model_record(ExpenditureItem, id)
    expenditure_id = expenditure_item.expenditure.id if getattr(expenditure_item, "expenditure", None) else None

    # Delete then redirect back to the parent expenditure items page
    expenditure_item.delete()
    messages.success(request, DELETE_MESSAGE)

    if expenditure_id:
        return HttpResponsePermanentRedirect(reverse(manage_expenditure_items, args=[expenditure_id]))
    # Fallback: go to expenditures list if parent missing
    return HttpResponsePermanentRedirect(reverse(manage_expenditures))

@login_required
def manage_vendors(request):
    form = finance_forms.VendorForm()
    vendors = get_all_model_records(Vendor)
    
    context = {
        "vendors": vendors,
        "form": form
    }
    return render(request, "finance/vendors.html", context)

@login_required
def add_vendor(request):
    if request.method == "POST":
        form = finance_forms.VendorForm(request.POST, request.FILES)
        
        if form.is_valid():
            form.save()
            
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
    
    return HttpResponsePermanentRedirect(reverse(manage_vendors))


@login_required
def edit_vendors(request, id):
    vendor = get_model_record(Vendor, id)
    if request.method=="POST":
        form = finance_forms.VendorForm(request.POST, request.FILES, instance=vendor)
    
        if form.is_valid():
           form.save()
           messages.success(request, SUCCESS_ADD_MESSAGE)
           return HttpResponsePermanentRedirect(reverse(manage_vendors))
        else:
           messages.error(request, FAILURE_MESSAGE)
           
    else:
        form = finance_forms.VendorForm(instance=vendor)
        
    context={
        "form": form,
        "vendor": vendor        
    }
    return render(request,"finance/edit_vendor.html",context)
    
  

def delete_vendor(request, id):
    vendor = get_model_record(Vendor, id)
    
    vendor.delete()
    messages.success(request, DELETE_MESSAGE)
    
    return HttpResponsePermanentRedirect(reverse(manage_vendors))

@login_required
def manage_budgets(request):
    form = finance_forms.BudgetForm()
    budgets = get_all_model_records(Budget)
    
    context = {
        "budgets": budgets,
        "form": form
    }
    return render(request, "finance/budgets.html", context)

@login_required
def add_budget(request):
    if request.method == "POST":
        form = finance_forms.BudgetForm(request.POST, request.FILES)
        
        if form.is_valid():
            form.save()
            
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
    
    return HttpResponsePermanentRedirect(reverse(manage_budgets))


@login_required
def edit_budgets(request, id):
    budget = get_model_record(Budget,id)
    if request.method=="POST":
        form = finance_forms.BudgetForm(request.POST, request.FILES, instance=budget)
        
        if form.is_valid():
            form.save()
            messages.success(request,SUCCESS_ADD_MESSAGE)
            return HttpResponsePermanentRedirect(reverse(manage_budgets))
        else:
            messages.error(request,FAILURE_MESSAGE)
  
    form = finance_forms.BudgetForm(instance=budget)
        
    context={
        "form":form,
        "budget":budget
    }
    return render(request,"finance/edit_budget_page.html",context)


def delete_budget(request, id):
    budget = get_model_record(Budget, id)
    
    budget.delete()
    messages.success(request, DELETE_MESSAGE)
    
    return HttpResponsePermanentRedirect(reverse(manage_budgets))

@login_required
def manage_budget_items(request, id):
    budget = get_model_record(Budget, id)
    form = finance_forms.BudgetItemForm(initial={"budget": budget})
    budget_items = finance_selector.get_budget_items(budget)
    
    context = {
        "budget_items": budget_items,
        "form": form,
        "budget": budget
    }
    return render(request, "finance/budget_items.html", context)

@login_required
def add_budget_item(request):
    if request.method == "POST":
        form = finance_forms.BudgetItemForm(request.POST)
        budget = request.POST["budget"]
        
        if form.is_valid():
            item = form.save()
            
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
    
    return HttpResponsePermanentRedirect(reverse(manage_budget_items, args=[budget]))


@login_required
def edit_budget_items(request, id):
    budget_item = get_model_record(BudgetItem, id)
    if request.method=="POST":
        form = finance_forms.BudgetItemForm(request.POST, instance=budget_item)
    
        if form.is_valid():
           form.save()
           messages.success(request, SUCCESS_ADD_MESSAGE)
    
        else:
            messages.error(request, FAILURE_MESSAGE)
            return HttpResponsePermanentRedirect(reverse(manage_budget_items, args=[budget_item.budget.id]))    
           
    form = finance_forms.BudgetItemForm(instance=budget_item)
    
    context={
        "form": form,
        "budget_item": budget_item
    }
    return render(request,"finance/edit_budget_item.html",context)
           

def delete_budget_item(request, id):
    budget_item = get_model_record(BudgetItem, id)
    
    budget_item.delete()
    messages.success(request, DELETE_MESSAGE)
    
    return HttpResponsePermanentRedirect(reverse(manage_budget_items, args=[budget_item.budget.id]))





@login_required
def financial_summary_report(request):
    # Get filter parameters
    academic_year_id = request.GET.get('academic_year')
    term_id = request.GET.get('term')

    # Get all academic years and terms for filter dropdowns
    academic_years = get_all_model_records(AcademicYear)
    terms = get_all_model_records(Term)

    # Default to current if no filters
    if not academic_year_id:
        current_year = AcademicYear.objects.filter(is_current=True).first()
        academic_year_id = current_year.id if current_year else None

    if not term_id:
        current_term = Term.objects.filter(is_current=True).first()
        term_id = current_term.id if current_term else None

    # Initialize data structures
    class_data = []
    total_school_fees_billed = 0
    total_school_fees_collected = 0
    total_other_fees_collected = 0
    total_outstanding = 0
    total_other_income = 0
    total_expenditure = 0
    department_breakdown = {}
    total_other_fees_billed_global = 0  # Global accumulator for other fees billed
    over_expenditure_alerts = []

    if academic_year_id and term_id:
        academic_year = get_model_record(AcademicYear, academic_year_id)
        term = get_model_record(Term, term_id)

        # Get all academic classes for the selected year and term
        academic_classes = AcademicClass.objects.filter(
            academic_year=academic_year,
            term=term
        ).select_related('Class', 'section')

        for academic_class in academic_classes:
            # Get all student bills for this class with related items
            student_bills = StudentBill.objects.filter(
                academic_class=academic_class
            ).select_related('student').prefetch_related('items')

            # Get class bills for this academic class
            class_bills = ClassBill.objects.filter(
                academic_class=academic_class
            ).select_related('bill_item')

            num_students = student_bills.count()

            # Calculate school fees from actual bill items instead of using academic_class.fees_amount
            # This ensures it matches the dashboard calculation
            class_school_fees_billed = 0
            for bill in student_bills:
                for item in bill.items.all():
                    if ('tuition' in item.description.lower() or 'school' in item.description.lower() or 'fee' in item.description.lower()):
                        class_school_fees_billed += item.amount

            # Define school_fees_per_student for template context (use academic class amount for display)
            school_fees_per_student = academic_class.fees_amount

            # Calculate other fees from both StudentBillItem and ClassBill
            total_other_fees_billed = 0
            total_school_fees_collected_for_class = 0
            total_other_fees_collected_for_class = 0
            total_collected_for_class = 0
            total_outstanding_for_class = 0

            # Track students with other fees
            students_with_other_fees = 0

            # Process ClassBill for other fees (applied to all students)
            for class_bill in class_bills:
                if not ('tuition' in class_bill.bill_item.description.lower() or 'school' in class_bill.bill_item.description.lower() or 'fee' in class_bill.bill_item.description.lower()):
                    # This is applied to all students in the class
                    total_other_fees_billed += (class_bill.amount * num_students)

            # Process each student's bill items for additional other fees and payments
            for bill in student_bills:
                student_has_other_fees = False
                school_fees_for_student = 0
                other_fees_for_student = 0

                # Check each bill item for other fees (books, uniform, transport, etc.)
                for item in bill.items.all():
                    # Only count non-school fee items as other income
                    if not ('tuition' in item.description.lower() or 'school' in item.description.lower() or 'fee' in item.description.lower()):
                        total_other_fees_billed += item.amount
                        other_fees_for_student += item.amount
                        student_has_other_fees = True
                    else:
                        # This is a school fee item
                        school_fees_for_student += item.amount

                # Count students who have other fees
                if student_has_other_fees:
                    students_with_other_fees += 1

                # Simply use the actual payment amount as recorded
                # Don't try to allocate proportionally - use the payment as-is
                total_payment = bill.amount_paid
                total_collected_for_class += total_payment
                total_outstanding_for_class += bill.balance

                # For reporting purposes, assume all payments contribute to school fees collection
                # This gives a realistic view of collection performance
                total_school_fees_collected_for_class += total_payment

            # Calculate average other fees per student (only for students who have other fees)
            other_fees_per_student = total_other_fees_billed / students_with_other_fees if students_with_other_fees > 0 else 0

            # Calculate total collected for the class (both school and other fees)
            total_collected_for_class = total_school_fees_collected_for_class + total_other_fees_collected_for_class

            # Calculate collection rate: total collected / total billed
            # Use the actual payment amounts as recorded for realistic percentages
            total_billed_for_class = class_school_fees_billed + total_other_fees_billed
            collection_rate = (total_collected_for_class / total_billed_for_class * 100) if total_billed_for_class > 0 else 0

            class_data.append({
                'class_name': str(academic_class),
                'school_fees_per_student': school_fees_per_student,
                'other_fees_per_student': round(other_fees_per_student, 2),
                'num_students': num_students,
                'students_with_other_fees': students_with_other_fees,
                'total_school_fees': class_school_fees_billed,
                'total_other_fees': total_other_fees_billed,
                'total_collected': total_collected_for_class,
                'outstanding': total_outstanding_for_class,
                'collection_rate': round(collection_rate, 1)
            })

            total_school_fees_billed += class_school_fees_billed
            total_school_fees_collected += total_school_fees_collected_for_class
            total_other_fees_collected += total_other_fees_collected_for_class
            total_outstanding += total_outstanding_for_class
            # Add collected other fees to other income (not billed amount)
            total_other_income += total_other_fees_collected_for_class
            # Accumulate other fees billed globally
            total_other_fees_billed_global += total_other_fees_billed

            # Accumulate other fees billed globally
            total_other_fees_billed_global += total_other_fees_billed

        # Other income is now calculated from non-school fee bill items above
        # (books, uniform, transport, etc. are considered other income, not school fees)

        # Expenditures for the selected period
        budget = Budget.objects.filter(
            academic_year=academic_year,
            term=term
        ).first()

        expenditure_data = []
        budget_item_data = []

        if budget:
            # Get detailed expenditure data
            expenditures = Expenditure.objects.filter(
                budget_item__budget=budget
            ).select_related('budget_item__expense', 'budget_item__department')

            # Group expenditures by budget item
            expenditure_by_item = {}
            for expenditure in expenditures:
                item_key = expenditure.budget_item.id
                if item_key not in expenditure_by_item:
                    expenditure_by_item[item_key] = {
                        'budget_item': expenditure.budget_item,
                        'total_spent': 0,
                        'expenditures': []
                    }
                expenditure_by_item[item_key]['total_spent'] += expenditure.amount
                expenditure_by_item[item_key]['expenditures'].append(expenditure)
                total_expenditure += expenditure.amount

            # Get all budget items with expenditure data
            budget_items = BudgetItem.objects.filter(
                budget=budget
            ).select_related('department', 'expense')

            for item in budget_items:
                item_expenditure = expenditure_by_item.get(item.id, {'total_spent': 0, 'expenditures': []})

                # Calculate utilization percentage
                utilization = 0
                if item.allocated_amount > 0:
                    utilization = (item_expenditure['total_spent'] / item.allocated_amount) * 100

                budget_item_data.append({
                    'budget_item': item,
                    'allocated': item.allocated_amount,
                    'spent': item_expenditure['total_spent'],
                    'remaining': item.remaining_amount,
                    'utilization': round(utilization, 1),
                    'expenditures': item_expenditure['expenditures']
                })

                # Flag over-expenditure alerts
                if item_expenditure['total_spent'] > item.allocated_amount:
                    over_expenditure_alerts.append({
                        'department': str(item.department),
                        'expense': str(item.expense),
                        'allocated': item.allocated_amount,
                        'spent': item_expenditure['total_spent'],
                        'over_by': item_expenditure['total_spent'] - item.allocated_amount,
                        'utilization': round(utilization, 1),
                    })

                # Department breakdown for existing logic
                dept_name = str(item.department)
                if dept_name not in department_breakdown:
                    department_breakdown[dept_name] = {
                        'allocated': 0,
                        'spent': 0,
                        'remaining': 0,
                        'utilization': 0
                    }
                department_breakdown[dept_name]['allocated'] += item.allocated_amount
                department_breakdown[dept_name]['spent'] += item.amount_spent
                department_breakdown[dept_name]['remaining'] += item.remaining_amount

                # Calculate utilization for department
                if department_breakdown[dept_name]['allocated'] > 0:
                    department_breakdown[dept_name]['utilization'] = round((department_breakdown[dept_name]['spent'] / department_breakdown[dept_name]['allocated']) * 100, 1)
                else:
                    department_breakdown[dept_name]['utilization'] = 0


    total_income = total_school_fees_collected + total_other_income
    net_balance = total_income - total_expenditure

    # Calculate overall collection rate using actual payments received
    total_billed = total_school_fees_billed + total_other_fees_billed_global
    total_collected = total_income  # This is already school_fees_collected + other_income
    collection_rate = (total_collected / total_billed * 100) if total_billed > 0 else 0

    # Calculate budget utilization
    total_allocated = sum(item['allocated'] for item in budget_item_data) if budget_item_data else 0
    budget_utilization = (total_expenditure / total_allocated * 100) if total_allocated > 0 else 0

    # Calculate remaining budget explicitly
    remaining_budget = total_allocated - total_expenditure


    # Data Quality Validation
    data_quality_warnings = []

    # Check collection rate
    if collection_rate > 150:
        data_quality_warnings.append({
            'type': 'warning',
            'message': f'Collection rate ({collection_rate:.1f}%) is unusually high. This may indicate data quality issues.',
            'severity': 'high'
        })

    # Check outstanding balance ratio
    outstanding_ratio = (total_outstanding / total_income * 100) if total_income > 0 else 0
    if outstanding_ratio > 100:
        data_quality_warnings.append({
            'type': 'warning',
            'message': f'Outstanding balance (UGX {total_outstanding:,}) is {outstanding_ratio:.1f}% of total revenue. This seems unusually high.',
            'severity': 'high'
        })

    # Check for classes with unrealistic collection rates
    unrealistic_classes = []
    for class_info in class_data:
        if class_info['collection_rate'] > 200:  # Over 200% is definitely suspicious
            unrealistic_classes.append(f"{class_info['class_name']} ({class_info['collection_rate']:.1f}%)")

    if unrealistic_classes:
        data_quality_warnings.append({
            'type': 'error',
            'message': f'Classes with unrealistic collection rates: {", ".join(unrealistic_classes)}. Please verify payment data.',
            'severity': 'critical'
        })

    # Check if collected amounts are way higher than billed
    if total_collected > total_billed * 2:
        data_quality_warnings.append({
            'type': 'warning',
            'message': f'Total collected (UGX {total_collected:,}) is more than double the billed amount (UGX {total_billed:,}). This may indicate payment misallocation.',
            'severity': 'medium'
        })

    # Overall data quality assessment
    if data_quality_warnings:
        overall_quality = 'poor' if any(w['severity'] == 'critical' for w in data_quality_warnings) else 'fair'
    else:
        overall_quality = 'good'

    # Get names for display
    academic_year_name = academic_year.academic_year if academic_year_id and term_id else None
    term_name = term.term if academic_year_id and term_id else None

    context = {
        'academic_years': academic_years,
        'terms': terms,
        'selected_academic_year': academic_year_id,
        'selected_term': term_id,
        'academic_year_name': academic_year_name,
        'term_name': term_name,
        'class_data': class_data,
        'total_school_fees_billed': total_school_fees_billed,
        'total_school_fees_collected': total_school_fees_collected,
        'total_other_fees_collected': total_other_fees_collected,
        'total_outstanding': total_outstanding,
        'total_other_income': total_other_income,
        'total_income': total_income,
        'total_expenditure': total_expenditure,
        'net_balance': net_balance,
        'department_breakdown': department_breakdown,
        'budget_item_data': budget_item_data,
        'total_allocated': total_allocated,
        'remaining_budget': remaining_budget,
        'collection_rate': round(collection_rate, 2),
        'budget_utilization': round(budget_utilization, 2),
        'data_quality_warnings': data_quality_warnings,
        'overall_quality': overall_quality,
        'over_expenditure_alerts': over_expenditure_alerts,
        # Debug information
        'debug_info': {
            'total_billed': total_billed,
            'total_collected': total_collected,
            'total_income': total_income,
            'total_school_fees_billed': total_school_fees_billed,
            'total_other_fees_billed_global': total_other_fees_billed_global,
            'total_other_income': total_other_income,
            'net_balance': net_balance,
            'collection_rate_calc': f"{total_collected}/{total_billed} = {collection_rate:.1f}%" if total_billed > 0 else "No fees billed",
            'calculation_explanation': 'total_billed = school_fees_billed + other_fees_billed_global, total_collected = school_fees_collected + other_fees_collected'
        }
    }

    # CSV export
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        filename_parts = []
        if academic_year_name:
            filename_parts.append(str(academic_year_name))
        if term_name:
            filename_parts.append(str(term_name))
        suffix = "_".join(filename_parts) if filename_parts else "all"
        response['Content-Disposition'] = f'attachment; filename="financial_summary_{suffix}.csv"'
        writer = csv.writer(response)

        # Executive summary section
        writer.writerow(['Financial Summary'])
        writer.writerow(['Academic Year', academic_year_name or ''])
        writer.writerow(['Term', term_name or ''])
        writer.writerow(['Total Revenue', total_income])
        writer.writerow(['Total Expenditure', total_expenditure])
        writer.writerow(['Net Balance', net_balance])
        writer.writerow(['Collection Rate (%)', round(collection_rate, 2)])
        writer.writerow(['Budget Utilization (%)', round(budget_utilization, 2)])
        writer.writerow([])

        # Class collection breakdown
        writer.writerow(['Class', 'Tuition per Student', 'Other Fees per Student', 'Students', 'Total Tuition Billed', 'Total Other Fees', 'Total Collected', 'Outstanding', 'Collection Rate (%)'])
        for c in class_data:
            writer.writerow([
                c.get('class_name', ''),
                c.get('school_fees_per_student', 0),
                c.get('other_fees_per_student', 0),
                c.get('num_students', 0),
                c.get('total_school_fees', 0),
                c.get('total_other_fees', 0),
                c.get('total_collected', 0),
                c.get('outstanding', 0),
                c.get('collection_rate', 0),
            ])
        writer.writerow([])

        # Budget items with utilization
        writer.writerow(['Department', 'Expense', 'Allocated', 'Spent', 'Remaining', 'Utilization (%)'])
        for bi in budget_item_data:
            writer.writerow([
                str(bi['budget_item'].department),
                str(bi['budget_item'].expense),
                bi.get('allocated', 0),
                bi.get('spent', 0),
                bi.get('remaining', 0),
                bi.get('utilization', 0),
            ])
        writer.writerow([])

        # Over-expenditure alerts
        if over_expenditure_alerts:
            writer.writerow(['Over-expenditure Alerts'])
            writer.writerow(['Department', 'Expense', 'Allocated', 'Spent', 'Over By', 'Utilization (%)'])
            for a in over_expenditure_alerts:
                writer.writerow([
                    a.get('department', ''),
                    a.get('expense', ''),
                    a.get('allocated', 0),
                    a.get('spent', 0),
                    a.get('over_by', 0),
                    a.get('utilization', 0),
                ])

        return response

    return render(request, 'finance/financial_summary_report.html', context)
           
           





@login_required
def vendor_payments_report(request):
    """
    Vendor Payments Report with optional vendor and date filters, plus CSV export.
    Non-destructive: reads existing Expenditures and aggregates by vendor.
    """
    vendor_id = request.GET.get('vendor')
    start_date_str = request.GET.get('start_date') or ''
    end_date_str = request.GET.get('end_date') or ''

    start_date = parse_date(start_date_str) if start_date_str else None
    end_date = parse_date(end_date_str) if end_date_str else None

    vendors = get_all_model_records(Vendor)

    expenditures_qs = (
        Expenditure.objects.select_related('vendor', 'budget_item__department', 'budget_item__expense')
        .filter(vendor__isnull=False)
        .order_by('-date_incurred', '-id')
    )

    if vendor_id:
        expenditures_qs = expenditures_qs.filter(vendor_id=vendor_id)
    if start_date:
        expenditures_qs = expenditures_qs.filter(date_incurred__gte=start_date)
    if end_date:
        expenditures_qs = expenditures_qs.filter(date_incurred__lte=end_date)

    # Aggregate in Python since Expenditure.amount is a computed property
    vendor_summary = {}
    total_spent = 0
    breakdown = list(expenditures_qs)

    for e in breakdown:
        amt = e.amount
        total_spent += amt
        key = e.vendor_id
        if key not in vendor_summary:
            vendor_summary[key] = {'vendor': e.vendor, 'count': 0, 'total': 0}
        vendor_summary[key]['count'] += 1
        vendor_summary[key]['total'] += amt

    summary = sorted(
        [{'vendor': v['vendor'], 'count': v['count'], 'total': v['total']} for v in vendor_summary.values()],
        key=lambda x: x['total'],
        reverse=True
    )
    # Add percentage share per vendor (of total spent) for template display
    for row in summary:
        row['pct'] = round((row['total'] / total_spent * 100), 1) if total_spent else 0

    # CSV export
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        filename_parts = ['vendor_payments']
        if vendor_id:
            try:
                vendor_obj = Vendor.objects.get(id=vendor_id)
                filename_parts.append(vendor_obj.name.replace(' ', '_'))
            except Vendor.DoesNotExist:
                pass
        if start_date_str:
            filename_parts.append(f"from_{start_date_str}")
        if end_date_str:
            filename_parts.append(f"to_{end_date_str}")
        fname = "_".join(filename_parts) if filename_parts else "vendor_payments"
        response['Content-Disposition'] = f'attachment; filename="{fname}.csv"'
        writer = csv.writer(response)

        writer.writerow(['Vendor Payments Summary'])
        writer.writerow(['Vendor', 'Transactions', 'Total Spent'])
        for row in summary:
            writer.writerow([
                row['vendor'].name if row['vendor'] else '',
                row['count'],
                row['total'],
            ])
        writer.writerow([])

        writer.writerow(['Detailed Expenditures'])
        writer.writerow(['Date', 'Vendor', 'Department', 'Expense', 'Description', 'Amount', 'VAT'])
        for e in breakdown:
            writer.writerow([
                e.date_incurred,
                e.vendor.name if e.vendor else '',
                str(e.budget_item.department) if e.budget_item else '',
                str(e.budget_item.expense) if e.budget_item else '',
                e.description,
                e.amount,
                e.vat,
            ])
        return response

    context = {
        'vendors': vendors,
        'selected_vendor': int(vendor_id) if vendor_id else None,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'summary': summary,
        'breakdown': breakdown,
        'total_spent': total_spent,
    }
    return render(request, 'finance/vendor_report.html', context)

@login_required
def approve_expenditure(request, id):
    """Approve an expenditure by setting the approved_by field to the current user."""
    expenditure = get_model_record(Expenditure, id)
    if request.method == "POST":
        approver = ""
        try:
            approver = request.user.get_full_name()
        except Exception:
            pass
        approver = approver or getattr(request.user, "username", str(request.user))

        expenditure.approved_by = approver
        expenditure.save(update_fields=["approved_by"])
        messages.success(request, "Expenditure approved successfully.")
    else:
        messages.error(request, "Invalid request method. Use POST to approve.")
    return HttpResponsePermanentRedirect(reverse(manage_expenditures))


@login_required
def revoke_expenditure_approval(request, id):
    """Revoke approval for an expenditure by clearing the approved_by field."""
    expenditure = get_model_record(Expenditure, id)
    if request.method == "POST":
        expenditure.approved_by = None
        expenditure.save(update_fields=["approved_by"])
        messages.success(request, "Expenditure approval revoked.")
    else:
        messages.error(request, "Invalid request method. Use POST to revoke approval.")
    return HttpResponsePermanentRedirect(reverse(manage_expenditures))

@login_required
def income_statement_report(request):
    """
    Income Statement using Transaction model, with date filters and CSV export.
    Non-destructive: reads existing Transactions; does not mutate data.
    """
    start_date_str = request.GET.get('start_date') or ''
    end_date_str = request.GET.get('end_date') or ''
    start_date = parse_date(start_date_str) if start_date_str else None
    end_date = parse_date(end_date_str) if end_date_str else None

    used_term_default = False
    # Default to current term when no explicit range is provided
    if not (start_date and end_date):
        current_year = AcademicYear.objects.filter(is_current=True).first()
        current_term = Term.objects.filter(is_current=True, academic_year=current_year).first() if current_year else Term.objects.filter(is_current=True).first()
        if current_term and getattr(current_term, "start_date", None) and getattr(current_term, "end_date", None):
            start_date = current_term.start_date
            end_date = current_term.end_date
            start_date_str = start_date.isoformat()
            end_date_str = end_date.isoformat()
            used_term_default = True

    has_range = bool(start_date and end_date)
    # Toggle basis for Income Statement: 'accrual' (default) or 'cash'
    mode = (request.GET.get('mode') or 'accrual').lower()
    if mode not in ('accrual', 'cash'):
        mode = 'accrual'
    # Toggle basis for Income Statement: 'accrual' (default) or 'cash'
    mode = (request.GET.get('mode') or 'accrual').lower()
    if mode not in ('accrual', 'cash'):
        mode = 'accrual'

    if has_range:
        tx_qs = (
            Transaction.objects.all()
            .order_by('date')
            .filter(date__gte=start_date, date__lte=end_date)
        )
    else:
        tx_qs = Transaction.objects.none()

    # Build Income Statement data based on selected mode
    class SimpleIncome:
        def __init__(self, date, description, amount, source_name='School fees'):
            self.date = date
            self.description = description
            self.amount = amount
            # minimal object with .name for template compatibility
            self.related_income_source = type('Src', (), {'name': source_name})()

    class SimpleExpense:
        def __init__(self, date, description, amount):
            self.date = date
            self.description = description
            self.amount = amount

    if mode == 'accrual':
        # Revenue: billed (earned) within date range (student bill items by bill date)
        billed_qs = StudentBillItem.objects.filter(
            bill__bill_date__gte=start_date,
            bill__bill_date__lte=end_date
        ).select_related('bill')

        income_list = [
            SimpleIncome(
                sbi.bill.bill_date,
                sbi.description,
                sbi.amount
            ) for sbi in billed_qs
        ]
    
        # Group identical accrual income rows by (date, description, source) to avoid visually noisy duplicates
        if mode == 'accrual':
            buckets = {}
            for r in income_list:
                key = (r.date, r.description, getattr(r.related_income_source, 'name', ''))
                if key in buckets:
                    buckets[key].amount += r.amount
                else:
                    buckets[key] = SimpleIncome(
                        r.date,
                        r.description,
                        r.amount,
                        getattr(r.related_income_source, 'name', 'School fees')
                    )
            income_list = [buckets[k] for k in sorted(buckets.keys(), key=lambda x: (x[0], x[1]))]

        # Expenses: incurred within date range
        expenditures_qs = Expenditure.objects.filter(
            date_incurred__gte=start_date,
            date_incurred__lte=end_date
        ).select_related('vendor')

        expense_list = [
            SimpleExpense(
                e.date_incurred,
                f"Expenditure#{e.id} {(e.vendor.name if e.vendor else 'No vendor')}",
                e.amount
            ) for e in expenditures_qs
        ]
    else:
        # Cash mode: revenue = payments received in range; expenses = actually paid only
        payments_qs = Payment.objects.filter(
            payment_date__gte=start_date,
            payment_date__lte=end_date
        )
        income_list = [
            SimpleIncome(
                p.payment_date,
                f"Student payment bill#{p.bill_id} ref {p.reference_no}",
                p.amount
            ) for p in payments_qs
        ]

        expenditures_paid_qs = Expenditure.objects.filter(
            payment_status='Paid',
            date_recorded__gte=start_date,
            date_recorded__lte=end_date
        ).select_related('vendor')

        expense_list = [
            SimpleExpense(
                e.date_recorded,
                f"Expenditure#{e.id} {(e.vendor.name if e.vendor else 'No vendor')}",
                e.amount
            ) for e in expenditures_paid_qs
        ]

    # Totals
    total_income = sum((i.amount for i in income_list), 0)
    total_expense = sum((e.amount for e in expense_list), 0)
    net_income = total_income - total_expense

    # Income by Source (single category unless you later add more sources)
    income_breakdown = [{'source': 'School fees', 'total': total_income}]
    income_breakdown.sort(key=lambda x: x['total'], reverse=True)

    # CSV export
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        parts = ['income_statement']
        if start_date_str:
            parts.append(f'from_{start_date_str}')
        if end_date_str:
            parts.append(f'to_{end_date_str}')
        fname = '_'.join(parts)
        response['Content-Disposition'] = f'attachment; filename="{fname}.csv"'
        w = csv.writer(response)

        w.writerow(['Income Statement'])
        w.writerow(['Start Date', start_date_str])
        w.writerow(['End Date', end_date_str])
        w.writerow(['Total Income', total_income])
        w.writerow(['Total Expense', total_expense])
        w.writerow(['Net Income', net_income])
        w.writerow([])

        w.writerow(['Income by Source'])
        w.writerow(['Source', 'Amount'])
        for row in income_breakdown:
            w.writerow([row['source'], row['total']])
        w.writerow([])

        w.writerow(['Income Transactions'])
        w.writerow(['Date', 'Description', 'Source', 'Amount'])
        for t in income_list:
            w.writerow([
                t.date,
                t.description,
                t.related_income_source.name if t.related_income_source else '',
                t.amount
            ])
        w.writerow([])

        w.writerow(['Expense Transactions'])
        w.writerow(['Date', 'Description', 'Amount'])
        for t in expense_list:
            w.writerow([t.date, t.description, t.amount])

        return response

    context = {
        'start_date': start_date_str,
        'end_date': end_date_str,
        'used_term_default': used_term_default,
        'mode': mode,
        'total_income': total_income,
        'total_expense': total_expense,
        'net_income': net_income,
        'income_breakdown': income_breakdown,
        'income_tx': income_list,
        'expense_tx': expense_list,
        # sample rows for notice banner
        'sample_income': income_list[:5],
        'sample_expense': expense_list[:5],
    }
    return render(request, 'finance/income_statement.html', context)

@login_required
def cash_flow_report(request):
    """
    Cash Flow Report using Transaction model with date filters and CSV export.
    Non-destructive: reads existing Transactions; does not mutate data.
    """
    start_date_str = request.GET.get('start_date') or ''
    end_date_str = request.GET.get('end_date') or ''
    start_date = parse_date(start_date_str) if start_date_str else None
    end_date = parse_date(end_date_str) if end_date_str else None

    # Default to current term when no explicit range is provided
    used_term_default = False
    if not (start_date and end_date):
        current_year = AcademicYear.objects.filter(is_current=True).first()
        current_term = Term.objects.filter(is_current=True, academic_year=current_year).first() if current_year else Term.objects.filter(is_current=True).first()
        if current_term and getattr(current_term, "start_date", None) and getattr(current_term, "end_date", None):
            start_date = current_term.start_date
            end_date = current_term.end_date
            start_date_str = start_date.isoformat()
            end_date_str = end_date.isoformat()
            used_term_default = True

    has_range = bool(start_date and end_date)
    if has_range:
        tx_qs = Transaction.objects.filter(date__gte=start_date, date__lte=end_date).order_by('date')
    else:
        tx_qs = Transaction.objects.none()

    # Cash basis: inflows from Payments; outflows only from actually paid Expenditures
    pay_qs = Payment.objects.filter(
        payment_date__gte=start_date,
        payment_date__lte=end_date
    )

    # If your workflow marks paid expenditures via payment_status, we approximate cash payments
    # using payment_status='Paid' and date_recorded as the paid date.
    exp_qs = Expenditure.objects.filter(
        payment_status='Paid',
        date_recorded__gte=start_date,
        date_recorded__lte=end_date
    ).select_related('vendor')

    class SimpleIncome:
        def __init__(self, date, description, amount):
            self.date = date
            self.description = description
            self.amount = amount

    class SimpleExpense:
        def __init__(self, date, description, amount):
            self.date = date
            self.description = description
            self.amount = amount

    income_list = [
        SimpleIncome(
            p.payment_date,
            f"Student payment bill#{p.bill_id} ref {p.reference_no}",
            p.amount
        ) for p in pay_qs
    ]
    expense_list = [
        SimpleExpense(
            e.date_recorded,
            f"Expenditure#{e.id} {(e.vendor.name if e.vendor else 'No vendor')}",
            e.amount
        ) for e in exp_qs
    ]

    # Totals
    total_income = sum((t.amount for t in income_list), 0)
    total_expenses = sum((t.amount for t in expense_list), 0)
    net_cash_flow = total_income - total_expenses

    # Daily net flow timeline (cash movements)
    flow_by_date = {}
    for t in income_list:
        key = t.date
        flow_by_date[key] = flow_by_date.get(key, 0) + t.amount
    for t in expense_list:
        key = t.date
        flow_by_date[key] = flow_by_date.get(key, 0) - t.amount

    daily_flow = [{'date': d, 'net': flow_by_date[d]} for d in sorted(flow_by_date.keys())]

    # CSV export
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        parts = ['cash_flow']
        if start_date_str:
            parts.append(f'from_{start_date_str}')
        if end_date_str:
            parts.append(f'to_{end_date_str}')
        fname = '_'.join(parts)
        response['Content-Disposition'] = f'attachment; filename="{fname}.csv"'
        w = csv.writer(response)

        w.writerow(['Cash Flow Report'])
        w.writerow(['Start Date', start_date_str])
        w.writerow(['End Date', end_date_str])
        w.writerow(['Total Income', total_income])
        w.writerow(['Total Expenses', total_expenses])
        w.writerow(['Net Cash Flow', net_cash_flow])
        w.writerow([])

        w.writerow(['Daily Net Flow'])
        w.writerow(['Date', 'Net'])
        for row in daily_flow:
            w.writerow([row['date'], row['net']])
        w.writerow([])

        w.writerow(['Income Transactions'])
        w.writerow(['Date', 'Description', 'Amount'])
        for t in income_list:
            w.writerow([t.date, t.description, t.amount])
        w.writerow([])

        w.writerow(['Expense Transactions'])
        w.writerow(['Date', 'Description', 'Amount'])
        for t in expense_list:
            w.writerow([t.date, t.description, t.amount])

        return response

    context = {
        'start_date': start_date_str,
        'end_date': end_date_str,
        'used_term_default': used_term_default,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'net_cash_flow': net_cash_flow,
        'daily_flow': daily_flow,
        'income_tx': income_list,
        'expense_tx': expense_list,
        # sample rows for notice banner
        'sample_income': income_list[:5],
        'sample_expense': expense_list[:5],
    }
    return render(request, 'finance/cash_flow.html', context)
