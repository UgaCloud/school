from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from app.models import AcademicClassStream, Staff, Subject
from app.models import Timetable, Classroom, WeekDay, TimeSlot, BreakPeriod


class SchoolTimetableView(ListView):
    model = Timetable
    template_name = 'timetable/school_timetable.html'
    context_object_name = 'timetables'

    def get_queryset(self):
        return Timetable.objects.all().order_by('weekday', 'time_slot')


class ClassTimetableView(ListView):
    model = Timetable
    template_name = 'timetable/class_timetable.html'
    context_object_name = 'timetables'

    def get_queryset(self):
        class_id = self.kwargs.get('class_id')
        return Timetable.objects.filter(class_stream__id=class_id).order_by('weekday', 'time_slot')


class TeacherTimetableView(ListView):
    model = Timetable
    template_name = 'timetable/teacher_timetable.html'
    context_object_name = 'timetables'

    def get_queryset(self):
        teacher_id = self.kwargs.get('teacher_id')
        return Timetable.objects.filter(teacher__id=teacher_id).order_by('weekday', 'time_slot')


class ClassroomListView(ListView):
    model = Classroom
    template_name = 'timetable/classrooms.html'
    context_object_name = 'classrooms'


class ClassroomDetailView(DetailView):
    model = Classroom
    template_name = 'timetable/classroom_detail.html'
    context_object_name = 'classroom'

