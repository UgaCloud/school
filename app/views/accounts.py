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
from core.settings import common
from django.views.generic import ListView
from app.selectors.model_selectors import *
from django.views.generic import DetailView
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.template.loader import render_to_string
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.mixins import LoginRequiredMixin
from app.models.classes import ClassSubjectAllocation



@login_required
def create_account_view(request):
    if request.method == 'POST':
        form = StaffAccountForm(request.POST)
        if form.is_valid():
            staff = form.cleaned_data['staff']

            first_initial = staff.first_name[0].upper()
            last_name = staff.last_name.lower()
            base_username = f"{first_initial}-{last_name}"
            unique_username = base_username
            counter = 1

            while User.objects.filter(username=unique_username).exists():
                unique_username = f"{base_username}{counter}"
                counter += 1

            # Create user account
            user = User.objects.create_user(
                username=unique_username,
                password='123',  # Default password
                first_name=staff.first_name,
                last_name=staff.last_name
            )
            staff.user = user  
            staff.save()
            messages.success(request, f"Account for {user.username} created successfully.")

            # Assign role if available
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
            error_message = "Invalid username or password. Please try again."
    else:
        form = CustomLoginForm()

    context = {
        'form': form,
        'school_settings': school_settings,
        'error_message': error_message,
    }
    return render(request, 'accounts/login.html', context)



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
    paginate_by = 150                  

    def get_queryset(self):
        # Optionally, add filters (e.g., only active users)
        queryset = User.objects.all().order_by('username')
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(username__icontains=search_query)
        return queryset


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'accounts/user_detail.html'
    context_object_name = 'viewed_user'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        viewed_user = self.object
        staff_account = StaffAccount.objects.filter(user=viewed_user).first()
        staff = staff_account.staff if staff_account else None

        # Get teaching assignments for staff
        teaching_assignments = ClassSubjectAllocation.objects.filter(subject_teacher=staff) if staff else None

        context['staff'] = staff
        context['role'] = staff_account.role if staff_account else None
        context['last_login'] = viewed_user.last_login
        context['teaching_assignments'] = teaching_assignments

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



class CustomPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset_form.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'

    def form_valid(self, form):
        email = form.cleaned_data.get('email')
        users = User.objects.filter(email=email)
        if not users.exists():
            messages.error(self.request, "No account found with that email.")
            return render(self.request, self.template_name, {'form': form})

        user = users.first()  
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(str(user.pk).encode()) 
        reset_url = f"{common.DEV_TUNNEL_URL}/password-reset/{uid}/{token}/"

        subject = "Password Reset Request"
        message = render_to_string(self.email_template_name, {
            'reset_url': reset_url,
            'user': user,
        })
        send_mail(subject, message, 'no-reply@yourdomain.com', [email])
        return super().form_valid(form)