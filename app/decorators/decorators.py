# decorators.py
from django.shortcuts import redirect
from functools import wraps

def role_required(role, function=None, redirect_to="/"):
    """
    Decorator for views that checks that the logged-in user has a specific role,
    redirects to the specified URL if necessary.
    """
    def test_func(user):
        if role == "admin":
            return user.is_superuser  # Adjusted to check for superuser status
        return getattr(user, f"is_{role.replace(' ', '_')}", False)

    @wraps(function)
    def wrapper(request, *args, **kwargs):
        if test_func(request.user):
            return function(request, *args, **kwargs)
        return redirect(redirect_to)

    return wrapper if function else test_func

# Adjusted specific role decorators
admin_required = lambda function=None, redirect_to="/": role_required("admin", function, redirect_to)
teacher_required = lambda function=None, redirect_to="/": role_required("teacher", function, redirect_to)
# Continue similarly for other roles...
