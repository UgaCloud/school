from django.shortcuts import render, HttpResponsePermanentRedirect,redirect
from django.urls import reverse
from django.contrib import messages
from app.constants import *
from app.models.finance import *
from app.forms.finance import *
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
    
    context = {
        "expenses": expenses,
        "form": form
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
    
    context = {
        "expenditures": expenditures,
        "form": form
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
    
    form = finance_forms.ExpenditureForm(request.POST, request.FILES, instance=expenditure)
    
    if form.is_valid():
        form.save()
            
        messages.success(request, SUCCESS_ADD_MESSAGE)
    else:
        messages.error(request, FAILURE_MESSAGE)
    
    return HttpResponsePermanentRedirect(reverse(manage_expenditures))

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




