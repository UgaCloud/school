from app.models.results import *
from django.db.models import Sum

def get_grade_and_points(score):
    grading = GradingSystem.objects.filter(min_score__lte=score, max_score__gte=score).first()
    if grading:
        return grading.grade, grading.points
    return "N/A", Decimal('0.00')

def get_current_mode():
    setting = ResultModeSetting.objects.first()
    return setting.mode if setting else "CUMULATIVE"

def get_performance_metrics(assessments):
    total_score = assessments.aggregate(total=Sum('score'))['total'] or Decimal('0.00')
    count = assessments.count()
    average = (total_score / count).quantize(Decimal('0.01')) if count > 0 else Decimal('0.00')

    ordered_assessments = assessments.order_by('-score')
    top_score = ordered_assessments.first()
    bottom_score = ordered_assessments.last()

    return {
        'average': average,
        'top_score': top_score.score if top_score else Decimal('0.00'),
        'bottom_score': bottom_score.score if bottom_score else Decimal('0.00'),
        'ordered_assessments': ordered_assessments
    }