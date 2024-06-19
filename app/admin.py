from django.contrib import admin

from app.models.school_settings import Section, AcademicYear
from app.models.classes import AcademicClass
# Register your models here.

admin.site.register(Section)
admin.site.register(AcademicYear)
admin.site.register(AcademicClass)