from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from app.models.school_settings import SchoolSetting


class GradingSystem(models.Model):
    min_score = models.DecimalField(max_digits=5, decimal_places=2)
    max_score = models.DecimalField(max_digits=5, decimal_places=2)
    grade = models.CharField(max_length=2)
    points = models.DecimalField(max_digits=4, decimal_places=2)

    def __str__(self):
        return f'{self.grade} ({self.min_score} - {self.max_score})'


class AssessmentType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    weight = models.DecimalField(max_digits=4, decimal_places=2)

    def __str__(self):
        return self.name


class Assessment(models.Model):
    academic_class = models.ForeignKey("app.AcademicClass", on_delete=models.CASCADE, related_name='assessments')
    assessment_type = models.ForeignKey("app.AssessmentType", on_delete=models.CASCADE, related_name='assessments')
    subject = models.ForeignKey("app.Subject", on_delete=models.CASCADE, related_name='assessments')
    date = models.DateField()
    out_of = models.IntegerField(default=100)
    is_done = models.BooleanField(default=False)

    class Meta:
        unique_together = ("academic_class", "assessment_type", "subject")

    def __str__(self):
        return f'{self.assessment_type} - {self.subject} {self.academic_class}'



class ResultModeSetting(models.Model):
    MODE_CHOICES = [
        ("CUMULATIVE", "Cumulative"),
        ("NON_CUMULATIVE", "Non-Cumulative"),
    ]

    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default="CUMULATIVE")

    def __str__(self):
        return f"Current Mode: {self.mode}"

    @classmethod
    def get_mode(cls):
        setting = cls.objects.first()
        return setting.mode if setting else "CUMULATIVE"

class Result(models.Model):
    assessment = models.ForeignKey("app.Assessment", on_delete=models.CASCADE, related_name='results')
    student = models.ForeignKey("app.Student", on_delete=models.CASCADE, related_name='results')
    score = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f'{self.student} - {self.assessment} - {self.score}'

    @property
    def grade(self):
        grading = GradingSystem.objects.filter(min_score__lte=self.score, max_score__gte=self.score).first()
        return grading.grade if grading else "N/A"

    @property
    def points(self):
        grading = GradingSystem.objects.filter(min_score__lte=self.score, max_score__gte=self.score).first()
        return grading.points if grading else Decimal('0.00')

    @property
    def actual_score(self):
        weight = self.assessment.assessment_type.weight
        mode = ResultModeSetting.get_mode()

        if mode == "CUMULATIVE":
            if weight > 0:
                return round((self.score / self.assessment.out_of) * weight, 0)
        elif mode == "NON_CUMULATIVE":
            return self.score

        return self.score


class ReportResults(models.Model):
    student = models.ForeignKey("app.Student", on_delete=models.CASCADE)
    subject = models.ForeignKey("app.Subject", on_delete=models.CASCADE)
    academic_class = models.ForeignKey("app.AcademicClass", on_delete=models.CASCADE, related_name='report_results')
    term = models.ForeignKey("app.Term", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.student} - {self.subject} - {self.academic_class}"

    def calculate_term_result(self):
    

        mode = ResultModeSetting.get_mode()
        details = self.details.all()

        if mode == "CUMULATIVE":
            total_score = sum(d.score for d in details)
            total_points = sum(d.points for d in details)
            return total_score, total_points

        elif mode == "NON_CUMULATIVE":
            return [(d.assessment_type.name, d.score) for d in details]


class ReportResultDetail(models.Model):
    report = models.ForeignKey(ReportResults, on_delete=models.CASCADE, related_name='details')
    assessment_type = models.ForeignKey("app.AssessmentType", on_delete=models.CASCADE)
    score = models.DecimalField(max_digits=5, decimal_places=2)
    points = models.DecimalField(max_digits=4, decimal_places=2)

    def __str__(self):
        return f"{self.report.student} - {self.assessment_type.name}: {self.score}"

class TermResult(models.Model):
    student = models.ForeignKey("app.Student", on_delete=models.CASCADE, related_name='term_results')
    academic_class = models.ForeignKey("app.AcademicClass", on_delete=models.CASCADE, related_name='term_results')
    total_score = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    average_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    total_points = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    rank_in_class = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f'{self.academic_class} - {self.student}'

    def calculate_term_result(self):
        """Calculate total and average scores, and total GPA points."""
        exam_results = self.student.results.filter(assessment__academic_class__term=self.term)
        total_score = sum(result.actual_score for result in exam_results)
        total_points = sum(result.points for result in exam_results)
        subjects_count = exam_results.count()
        self.total_score = total_score
        self.average_score = total_score / subjects_count if subjects_count > 0 else 0
        self.total_points = total_points
        self.save()

class AnnualResult(models.Model):
    student = models.ForeignKey("app.Student", on_delete=models.CASCADE, related_name='annual_results')
    academic_class = models.ForeignKey("app.AcademicClass", on_delete=models.CASCADE, related_name='annual_results')
    total_score = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    average_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    total_points = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    rank_in_class = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f'Annual Result - {self.student} - {self.academic_class.academic_year}'

    def calculate_annual_result(self):
        """Calculate total and average scores, and total GPA points for the academic year."""
        term_results = self.student.term_results.filter(term__academic_year=self.academic_year)
        total_score = sum(term_result.total_score for term_result in term_results)
        total_points = sum(term_result.total_points for term_result in term_results)
        term_count = term_results.count()

        self.total_score = total_score
        self.average_score = total_score / term_count if term_count > 0 else 0
        self.total_points = total_points
        self.save()

    def calculate_rank(self):
        """Optional: Calculate rank within the class based on total score."""
        all_results = AnnualResult.objects.filter(academic_year=self.academic_year, student__class_level=self.student.class_level)
        sorted_results = sorted(all_results, key=lambda x: x.total_score, reverse=True)
        for index, result in enumerate(sorted_results):
            if result.student == self.student:
                self.rank_in_class = index + 1
                self.save()
                break
