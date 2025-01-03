from django.contrib.auth.models import User
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from app.models.staffs import *
from django.utils.decorators import method_decorator
from app.decorators.decorators import *
from app.models.accounts import *
from app.models.school_settings import *
from django.contrib.auth.hashers import make_password
from django.contrib.auth import update_session_auth_hash,authenticate, login,logout
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import render, redirect
from django.contrib import messages
from app.forms.accounts import CustomLoginForm,RoleSwitchForm,StaffAccountForm
from app.views.index_views import *
from django.conf import settings
from django.views.generic import ListView
from app.selectors.model_selectors import *
from django.views.generic import DetailView
from django.template.loader import render_to_string
from django.http import JsonResponse


@login_required
def create_account_view(request):
    if request.method == 'POST':
        form = StaffAccountForm(request.POST)
        if form.is_valid():
            staff = form.cleaned_data['staff']

            
            username = (staff.last_name).lower()
            unique_username = username
            counter = 1

            
            while User.objects.filter(username=unique_username).exists():
                unique_username = f"{username}{counter}"
                counter += 1

            
            user = User.objects.create_user(
                username=unique_username,
                password='123',  # default password
                first_name=staff.first_name,
                last_name=staff.last_name
            )
            staff.user = user  
            staff.save()
            messages.success(request, f"Account for {user.username} created successfully.")

            
            role = staff.roles.first() if staff.roles.exists() else None

            if role:
                StaffAccount.objects.create(user=user, staff=staff, role=role)
            else:
                return JsonResponse({'error': "No role available for this staff member. Please assign a role."}, status=400)

            
            return JsonResponse({'success': True})

    else:
        form = StaffAccountForm()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('accounts/staff_account_form.html', {'form': form}, request=request)
        return JsonResponse({'form_html': html})
    return render(request, 'accounts/staff_account_form.html', {'form': form})




def user_login(request):
    error_message = None  
    school_settings = SchoolSetting.objects.first()

    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
        else:
            error_message ="Invalid username or password.Please try again."
    else:
        form = CustomLoginForm()
    context={
        'form':form,
        'school_settings':school_settings,
        'error_message': error_message,
    }
    return render(request, 'accounts/login.html',context)


@login_required
def dashboard(request):
    staff_account = StaffAccount.objects.get(user=request.user)

    roles = staff_account.staff.roles.all()
    current_role = staff_account.role

    return render(request, 'accounts/dashboards.html', {
        'roles': roles,
        'current_role': current_role
    })



@login_required
def switch_role(request):
    staff_account = get_object_or_404(StaffAccount, user=request.user)
    
    # Access the related Staff instance
    staff = staff_account.staff
    
    # Retrieve only the roles assigned to this Staff member
    assigned_roles = staff.roles.all()  # Assuming `roles` is a related field in Staff model

    if request.method == 'POST':
        form = RoleSwitchForm(request.POST)
        if form.is_valid():
            selected_role = form.cleaned_data['role']
            staff_account.role = selected_role 
            staff_account.save()
            return redirect(index_view)  
    else:
        
        form = RoleSwitchForm()
        form.fields['role'].queryset = assigned_roles  

    return render(request, 'accounts/switch_role.html', {'form': form})


def logout_view(request):
    logout(request)  
    return redirect('login')

class UserListView(ListView):
    model = User
    template_name = 'accounts/user_list.html'  
    context_object_name = 'users'     
    paginate_by = 10                  

    def get_queryset(self):
        # Optionally, add filters (e.g., only active users)
        queryset = User.objects.all().order_by('username')
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(username__icontains=search_query)
        return queryset



class UserDetailView(DetailView):
    model = User
    template_name = 'accounts/user_detail.html'
    context_object_name = 'user'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get the StaffAccount instance for the user
        staff_account = get_object_or_404(StaffAccount, user=self.object)
        
        # Retrieve the related Staff instance
        staff_member = staff_account.staff  # This will access the related Staff instance

        context['staff'] = staff_member  # Pass the Staff instance to the context
        context['roles'] = StaffAccount.objects.filter(user=self.object)  # Retrieve roles for the user
        context['last_login'] = self.object.last_login  
        return context

def delete_user_view(request, id):
    user = get_model_record(User,id)
    user.delete()
    messages.success(request, "User deleted successfully.")
    return HttpResponseRedirect(reverse('user_list'))


def password_change_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  
            messages.success(request, 'Your password has been updated successfully!')
            return redirect(index_view)  
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'accounts/password_change.html', {'form': form})



