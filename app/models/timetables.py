from django.db import models
from django.contrib.auth.models import User

class WeekDay(models.TextChoices):
    MONDAY = 'MON', 'Monday'
    TUESDAY = 'TUE', 'Tuesday'
    WEDNESDAY = 'WED', 'Wednesday'
    THURSDAY = 'THU', 'Thursday'
    FRIDAY = 'FRI', 'Friday'
    SATURDAY = 'SAT', 'Saturday'
    SUNDAY = 'SUN', 'Sunday'


class TimeSlot(models.Model):
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ['start_time']
        unique_together = ('start_time', 'end_time')

    def __str__(self):
        return f'{self.start_time.strftime("%H:%M")} - {self.end_time.strftime("%H:%M")}'


class Classroom(models.Model):
    name = models.CharField(max_length=50)
    location = models.CharField(max_length=100, verbose_name="Block", blank=True, null=True)
    capacity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name


class Timetable(models.Model):
    class_level = models.ForeignKey('ClassLevel', on_delete=models.CASCADE, related_name='timetables')
    academic_year = models.ForeignKey('AcademicYear', on_delete=models.CASCADE, related_name='timetables')

    def __str__(self):
        return f"{self.class_level} - {self.academic_year}"


class TimetableEntry(models.Model):
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name='entries')
    weekday = models.CharField(max_length=3, choices=WeekDay.choices)
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE)
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='teaching_slots')
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('timetable', 'weekday', 'time_slot')

    def __str__(self):
        return f'{self.subject} on {self.weekday} at {self.time_slot}'


class BreakPeriod(models.Model):
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name='breaks')
    weekday = models.CharField(max_length=3, choices=WeekDay.choices)
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)
    description = models.CharField(max_length=100, default="Break")

    class Meta:
        unique_together = ('timetable', 'weekday', 'time_slot')

    def __str__(self):
        return f'{self.description} on {self.weekday} at {self.time_slot}'
