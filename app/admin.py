from django.contrib import admin
from app.models.accounts import StaffAccount
from app.models.classes import *
from app.models.staffs import *
from app.models.results import *
from app.models.school_settings import *
from app.models.students import *
from django.utils.html import format_html

# admin.site.register(Staff)
admin.site.register(Role)
# admin.site.register(StaffAccount)
# admin.site.register(AcademicClass)
# admin.site.register(AcademicClassStream)
# admin.site.register(AcademicYear)
# admin.site.register(Term)
admin.site.register(Result)
admin.site.register(Assessment)
admin.site.register(AssessmentType)
# admin.site.register(Student)
admin.site.register(ClassRegister)
# admin.site.register(Section)
# admin.site.register(Class)
admin.site.register(Stream)
admin.site.register(SchoolSetting)



@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ('academic_year', 'is_current')
    list_filter = ('is_current',)
    search_fields = ('academic_year',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset  

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'section')
    list_filter = ('section',)
    search_fields = ('name', 'code', 'section__section_name')  

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('section')  
    
    
    #
@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('section_name',)
    search_fields = ('section_name',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset  


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = (
        'staff_photo_preview', 'first_name', 'last_name', 'email',
        'contacts', 'department', 'display_roles'
    )
    list_filter = ('department', 'gender')
    search_fields = ('first_name', 'last_name', 'email', 'contacts')
    readonly_fields = ('staff_photo_preview',)

    def staff_photo_preview(self, obj):
        if obj.staff_photo:
            return format_html('<img src="{}" style="height: 40px; border-radius: 5px;" />', obj.staff_photo.url)
        return "No Photo"
    staff_photo_preview.short_description = 'Photo'

    def display_roles(self, obj):
        return ", ".join([role.name for role in obj.roles.all()])
    display_roles.short_description = 'Roles'

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        'photo_preview', 'reg_no', 'student_name', 'gender',
        'current_class', 'contact', 'guardian'
    )
    list_filter = ('gender', 'current_class', 'academic_year')
    search_fields = ('reg_no', 'student_name', 'guardian', 'contact')
    readonly_fields = ('photo_preview',)

    def photo_preview(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="height: 40px; border-radius: 5px;" />', obj.photo.url)
        return "No Photo"
    photo_preview.short_description = 'Photo'


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ('term', 'academic_year', 'start_date', 'end_date', 'is_current')
    list_filter = ('academic_year', 'term', 'is_current')
    search_fields = ('term', 'academic_year__name')  
    readonly_fields = ('start_date', 'end_date')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('academic_year')  

@admin.register(AcademicClass)
class AcademicClassAdmin(admin.ModelAdmin):
    list_display = ('Class', 'term', 'academic_year', 'fees_amount')
    list_filter = ('Class', 'academic_year', 'term')
    search_fields = ('Class__name', 'academic_year__name', 'term__term')  
    readonly_fields = ('fees_amount',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('Class', 'academic_year', 'term')  

@admin.register(AcademicClassStream)
class AcademicClassStreamAdmin(admin.ModelAdmin):
    list_display = ('academic_class', 'stream', 'class_teacher')
    list_filter = ('academic_class', 'stream', 'class_teacher')
    search_fields = ('academic_class__Class__name', 'stream__name', 'class_teacher__first_name', 'class_teacher__last_name')  

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('academic_class', 'stream', 'class_teacher')
    
    

@admin.register(StaffAccount)
class StaffAccountAdmin(admin.ModelAdmin):
    list_display = ('staff', 'user', 'role')
    list_filter = ('role',)
    search_fields = ('staff__first_name', 'staff__last_name', 'user__username', 'user__email')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('staff', 'user', 'role')  

    def save_model(self, request, obj, form, change):
    
        super().save_model(request, obj, form, change)  