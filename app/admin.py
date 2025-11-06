from django.contrib import admin  
from app.models.accounts import StaffAccount
from app.models.classes import *
from app.models.staffs import *
from app.models.results import *
from app.models.school_settings import *
from app.models.students import *
from django.utils.html import format_html
from django.utils.safestring import mark_safe
import json
from .models import Classroom, TimeSlot, BreakPeriod, Timetable

# admin.site.register(Staff)
admin.site.register(Role)

admin.site.register(Result)
admin.site.register(Assessment)
admin.site.register(AssessmentType)
# admin.site.register(Student)
admin.site.register(ClassRegister)
# admin.site.register(Section)
# admin.site.register(Class)
admin.site.register(Stream)
admin.site.register(SchoolSetting)
admin.site.register(Department)



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
    # readonly_fields = ('start_date', 'end_date')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('academic_year')  

@admin.register(AcademicClass)
class AcademicClassAdmin(admin.ModelAdmin):
    list_display = ('Class', 'term', 'academic_year', 'fees_amount')
    list_filter = ('Class', 'academic_year', 'term')
    search_fields = ('Class__name', 'academic_year__name', 'term__term')  
    def get_readonly_fields(self, request, obj=None):
        # Allow editing fees_amount when adding a new AcademicClass
        # Keep it read-only on change to prevent accidental edits
        return ('fees_amount',) if obj else ()

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


# Register Classroom model
@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'capacity')
    list_filter = ('location',)
    search_fields = ('name', 'location')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset

# Register TimeSlot model
@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ('start_time', 'end_time')
    list_filter = ('start_time', 'end_time')
    search_fields = ('start_time', 'end_time')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset

# Register BreakPeriod model
@admin.register(BreakPeriod)
class BreakPeriodAdmin(admin.ModelAdmin):
    list_display = ('weekday', 'name', 'time_slot')
    list_filter = ('weekday',)
    search_fields = ('name', 'time_slot__start_time', 'time_slot__end_time')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('time_slot')

# Register Timetable model
@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = ('class_stream', 'subject', 'teacher', 'weekday', 'time_slot', 'classroom')
    list_filter = ('class_stream', 'weekday', 'time_slot', 'teacher', 'classroom')
    search_fields = ('class_stream__academic_class__Class__name', 'subject__name', 'teacher__first_name', 'teacher__last_name', 'classroom__name')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('class_stream', 'subject', 'teacher', 'classroom')

    def save_model(self, request, obj, form, change):
        # Additional actions before saving the object (if any)
        super().save_model(request, obj, form, change)




@admin.register(ResultModeSetting)
class ResultModeSettingAdmin(admin.ModelAdmin):
    list_display = ('mode',)
    actions = None 

    def has_add_permission(self, request):
        
        return not ResultModeSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):

        return False

    def get_queryset(self, request):

        return ResultModeSetting.objects.all()




















class ReportResultDetailInline(admin.TabularInline):
    model = ReportResultDetail
    extra = 1 
@admin.register(ReportResults)
class ReportResultsAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'academic_class', 'term', 'term_scores')
    list_filter = ('academic_class', 'term')
    search_fields = ('student__student_name', 'subject__name', 'academic_class__Class__name')
    inlines = [ReportResultDetailInline] 

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('student', 'subject', 'academic_class', 'term')

    def term_scores(self, obj):
        total_score, total_points = obj.calculate_term_result()
        return f"{total_score} / {total_points}"
    
    term_scores.short_description = "Total Scores"

# AuditLog Admin (read-only)
from app.models.audit import AuditLog


class SystemEntriesFilter(admin.SimpleListFilter):
    title = "System entries"
    parameter_name = "show_system"

    def lookups(self, request, model_admin):
        return (
            ("hide", "Hide system entries (default)"),
            ("show", "Show system entries"),
        )

    def queryset(self, request, queryset):
        return queryset


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    # Enhanced columns
    list_display = (
        "timestamp",
        "action_badge",
        "actor",
        "model_name",
        "object_short",
        "path_short",
        "changed_fields_summary",
        "ip_address",
        "method",
    )
    list_filter = ("action", "content_type", "user", "method", "ip_address", SystemEntriesFilter)
    search_fields = ("username", "object_repr", "object_id", "path", "ip_address", "user_agent")
    readonly_fields = (
        "timestamp",
        "action",
        "actor",
        "content_type",
        "object_id",
        "object_repr",
        "ip_address",
        "method",
        "path",
        "user",
        "username",
        "user_agent",
        "formatted_changes",
        "formatted_extra",
    )
    date_hierarchy = "timestamp"
    ordering = ("-timestamp",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        show = request.GET.get("show_system")
        if show != "show":
            qs = qs.exclude(content_type__app_label__in=["sessions", "admin"])
        return qs

    def action_badge(self, obj):
        action = (obj.action or "").lower()
        color = {
            "create": "success",
            "update": "warning",
            "delete": "danger",
            "login": "primary",
            "logout": "secondary",
        }.get(action, "info")
        label = (action or "-").capitalize()
        return format_html('<span class="badge badge-{}">{}</span>', color, label)
    action_badge.short_description = "Action"
    action_badge.admin_order_field = "action"


    def actor(self, obj):
        if obj.user_id and obj.user:
            if obj.username and obj.username != getattr(obj.user, "username", ""):
                return f"{obj.user} ({obj.username})"
            return str(obj.user)
        return obj.username or "-"
    actor.short_description = "Actor"

    # Column: Model (App | Model)
    def model_name(self, obj):
        if obj.content_type_id and obj.content_type:
            return f"{obj.content_type.app_label} | {obj.content_type.name}"
        return "-"
    model_name.short_description = "Content type"
    model_name.admin_order_field = "content_type"

    # Column: Object (short)
    def object_short(self, obj):
        text = obj.object_repr or obj.object_id or "-"
        if text and len(text) > 60:
            return f"{text[:57]}..."
        return text
    object_short.short_description = "Object"

    # Column: Path (short)
    def path_short(self, obj):
        p = obj.path or "-"
        if p != "-" and len(p) > 60:
            return f"{p[:57]}..."
        return p
    path_short.short_description = "Path"
    path_short.admin_order_field = "path"

    # Column: Changed fields summary
    def changed_fields_summary(self, obj):
        data = obj.changes or {}
        try:
            if isinstance(data, dict):
                if "new" in data or "old" in data:
                    # create/delete style payload
                    count = len(data.get("new") or data.get("old") or {})
                    if (obj.action or "").lower() == "create":
                        return f"Created: {count} fields"
                    if (obj.action or "").lower() == "delete":
                        return f"Deleted: {count} fields"
                    return f"{count} fields"
                # update style payload: { field: {old:..., new:...} }
                keys = list(data.keys())
                if not keys:
                    return "-"
                shown = ", ".join(keys[:5])
                more = len(keys) - 5
                return f"{shown}" + (f" +{more} more" if more > 0 else "")
        except Exception:
            pass
        return "-"
    changed_fields_summary.short_description = "Changed fields"

    # Detail: formatted JSON for changes
    def formatted_changes(self, obj):
        try:
            pretty = json.dumps(obj.changes, indent=2, ensure_ascii=False)
        except Exception:
            pretty = str(obj.changes)
        return format_html(
            '<pre style="white-space:pre-wrap;max-width:100%;overflow:auto;margin:0">{}</pre>',
            pretty,
        )
    formatted_changes.short_description = "Changes"

    # Detail: formatted JSON for extra
    def formatted_extra(self, obj):
        try:
            pretty = json.dumps(obj.extra, indent=2, ensure_ascii=False)
        except Exception:
            pretty = str(obj.extra)
        return format_html(
            '<pre style="white-space:pre-wrap;max-width:100%;overflow:auto;margin:0">{}</pre>',
            pretty,
        )
    formatted_extra.short_description = "Extra"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        # Fully read-only in admin
        return False

    def has_view_permission(self, request, obj=None):
        # Allow staff to view logs
        return request.user.is_active and request.user.is_staff
