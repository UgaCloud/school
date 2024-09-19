from django.contrib import admin

from app.models.accounts import StaffAccount
from app.models.classes import *
from app.models.staffs import *
from app.models.school_settings import *

admin.site.register(Staff)
admin.site.register(Role)
admin.site.register(StaffAccount)
admin.site.register(AcademicClass)
admin.site.register(AcademicClassStream)
admin.site.register(AcademicYear)
admin.site.register(Term)
