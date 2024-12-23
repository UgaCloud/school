from django.conf import settings

class UpdateJazzminMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from app.models.school_settings import SchoolSetting 
        school_name = (
            SchoolSetting.objects.first().school_name
            if SchoolSetting.objects.exists()
            else "Default School"
        )
        settings.JAZZMIN_SETTINGS["site_brand"] = school_name
        return self.get_response(request)
