from django.contrib import admin
from app.models.accounts import StaffAccount
from app.models.classes import *
from app.models.staffs import *
from app.models.results import *
from app.models.school_settings import *
from app.models.students import *

admin.site.register(Staff)
admin.site.register(Role)
admin.site.register(StaffAccount)
admin.site.register(AcademicClass)
admin.site.register(AcademicClassStream)
admin.site.register(AcademicYear)
admin.site.register(Term)
admin.site.register(Result)
admin.site.register(Assessment)
admin.site.register(AssessmentType)
admin.site.register(Student)
admin.site.register(ClassRegister)
admin.site.register(Section)
admin.site.register(Class)
admin.site.register(Stream)
admin.site.register(SchoolSetting)
admin.site.register(Department)