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
    expenditures = get_all_model_records(Expenditure)
    edit_forms = {expenditure.id: finance_forms.ExpenditureForm(instance=expenditure) for expenditure in expenditures}
    
    context = {
        "expenditures": expenditures,
        "form": form,
        "edit_forms": edit_forms
    }
    return render(request, "finance/expenditures.html", context)

@login_required
def add_expenditure(request):
    if request.method == "POST":
        form = finance_forms.ExpenditureForm(request.POST, request.FILES)
        
        if form.is_valid():
            expenditure = form.save()
            
            messages.success(request, SUCCESS_ADD_MESSAGE)
        else:
            messages.error(request, FAILURE_MESSAGE)
    
    return HttpResponsePermanentRedirect(reverse(manage_expenditure_items, args=[expenditure.id]))

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
    
    expenditure_item.delete()
    messages.success(request, DELETE_MESSAGE)
    
    return HttpResponsePermanentRedirect(reverse(manage_expenditure_items))

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

    return render(request, 'finance/financial_summary_report.html', context)
           
           




