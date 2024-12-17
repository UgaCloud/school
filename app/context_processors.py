from app.models.school_settings import SchoolSetting

def school_settings(request):
    school_settings = SchoolSetting.load()  # Use SingletonModel's `load()` method to get the instance
    return {
        'school_settings': school_settings
    }
