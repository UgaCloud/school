from app.models.school_settings import SchoolSetting

def school_settings(request):
    
    school_settings = SchoolSetting.load()  # Use SingletonModel's `load()` method to get the instance

    active_role = None
    try:
        if getattr(request, "user", None) and request.user.is_authenticated:
            # Prefer session active role 
            active_role = request.session.get("active_role_name")
            if not active_role:
                # Fallback to current StaffAccount role name when available
                staff_account = getattr(request.user, "staff_account", None)
                if staff_account and getattr(staff_account, "role", None):
                    active_role = staff_account.role.name
    except Exception:
        active_role = None

    return {
        'school_settings': school_settings,
        'active_role': active_role,
    }
