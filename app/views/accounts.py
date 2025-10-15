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



def pick_default_role(roles_qs):
    priorities = {name: idx for idx, name in enumerate(ROLE_PRIORITY)}
    best = None
    best_score = 10**6
    try:
        for role in roles_qs:
            score = priorities.get(getattr(role, "name", None), len(ROLE_PRIORITY) + 1)
            if score < best_score:
                best = role
                best_score = score
    except Exception:
        best = None
    # Fallback to first role if nothing matched
    if best is None and hasattr(roles_qs, "first"):
        return roles_qs.first()
    return best

def get_assigned_roles(user):
    try:
        return user.staff_account.staff.roles.all()
    except Exception:
        return Role.objects.none()


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
    """
    Authenticate user. On success
    """
    error_message = None
    school_settings = SchoolSetting.objects.first()

    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Determine default active role from assigned roles without changing DB
            roles = get_assigned_roles(user)
            picked = pick_default_role(roles)
            if picked:
                request.session['active_role_name'] = picked.name
            else:
                # Fallback to existing StaffAccount role name or Support Staff
                try:
                    request.session['active_role_name'] = user.staff_account.role.name
                except Exception:
                    request.session['active_role_name'] = 'Support Staff'

            return redirect('index_page')
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
    
    
    return redirect('index_page')



@login_required
def switch_role(request):
    """
    Switch the active role in SESSION only.
    """
    staff_account = get_object_or_404(StaffAccount, user=request.user)

    # Access the related Staff instance
    staff = staff_account.staff

    # Retrieve only the roles assigned to this Staff member
    assigned_roles = staff.roles.all()

    if request.method == 'POST':
        form = RoleSwitchForm(request.POST)
        # Limit choices to assigned roles for safety
        form.fields['role'].queryset = assigned_roles
        if form.is_valid():
            selected_role = form.cleaned_data['role']
            request.session['active_role_name'] = selected_role.name
            messages.success(request, f"Switched active role to {selected_role.name}.")
            return redirect(index_view)
        else:
            messages.error(request, "Invalid role selection.")
    else:
        form = RoleSwitchForm()
        form.fields['role'].queryset = assigned_roles

    return render(request, 'accounts/switch_role.html', {'form': form, 'roles': assigned_roles})


def logout_view(request):
    logout(request)  
    return redirect('login')

class UserListView(ListView):
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 12  # Better pagination for card layout

    def get_queryset(self):
        queryset = User.objects.all().order_by('-date_joined')  # Most recent first
        search_query = self.request.GET.get('search', '').strip()

        if search_query:
            queryset = queryset.filter(
                models.Q(username__icontains=search_query) |
                models.Q(first_name__icontains=search_query) |
                models.Q(last_name__icontains=search_query) |
                models.Q(email__icontains=search_query)
            )

        # Select related staff account and staff for better performance
        queryset = queryset.select_related('staff_account__staff')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add search query to context
        context['search_query'] = self.request.GET.get('search', '')

        # Add statistics
        all_users = User.objects.all()
        context['total_users'] = all_users.count()
        context['active_users'] = all_users.filter(is_active=True).count()
        context['inactive_users'] = all_users.filter(is_active=False).count()
        context['staff_users'] = all_users.filter(is_staff=True).count()
        context['superuser_count'] = all_users.filter(is_superuser=True).count()

        # Recent logins (last 30 days)
        from datetime import timedelta
        from django.utils import timezone
        thirty_days_ago = timezone.now() - timedelta(days=30)
        context['recent_logins'] = all_users.filter(last_login__gte=thirty_days_ago).count()

        return context


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'accounts/user_detail.html'
    context_object_name = 'viewed_user'

    def get_queryset(self):
        return super().get_queryset().select_related('staff_account__staff')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        viewed_user = self.object
        staff_account = viewed_user.staff_account if hasattr(viewed_user, 'staff_account') else None
        staff = staff_account.staff if staff_account else None

        # Get teaching assignments for staff with optimized queries
        if staff:
            teaching_assignments = ClassSubjectAllocation.objects.filter(
                subject_teacher=staff
            ).select_related(
                'academic_class_stream__academic_class__Class',
                'academic_class_stream__stream',
                'subject'
            ).order_by('academic_class_stream__academic_class__Class__name')
        else:
            teaching_assignments = None

        # Additional context data
        context.update({
            'staff': staff,
            'role': staff_account.role if staff_account else None,
            'last_login': viewed_user.last_login,
            'teaching_assignments': teaching_assignments,
            'is_admin': self.request.user.is_authenticated and
                       hasattr(self.request.user, 'staff_account') and
                       self.request.user.staff_account.role.name == "Admin",
            'account_age': viewed_user.date_joined,
        })

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