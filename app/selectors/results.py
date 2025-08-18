from app.models.results import *
from django.db.models import Sum
from decimal import Decimal

def get_grade_and_points(score):
    try:
        score = Decimal(str(score)).quantize(Decimal('0.01'))
        grade_row = GradingSystem.objects.filter(
            min_score__lte=score,
            max_score__gte=score
        ).order_by('min_score').first()
        if grade_row:
            return grade_row.grade, float(grade_row.points)
        return "N/A", 0
    except (ValueError, TypeError):
        return "N/A", 0






def get_current_mode():
    setting = ResultModeSetting.objects.first()
    return setting.mode if setting else "CUMULATIVE"

def get_performance_metrics(assessments):
    if not assessments.exists():
        return {
            'average': Decimal('0.00'),
            'top_score': Decimal('0.00'),
            'bottom_score': Decimal('0.00'),
            'ordered_assessments': []
        }
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

def get_grade_from_average(score):
    grading = GradingSystem.objects.filter(min_score__lte=score, max_score__gte=score).first()
    return grading.grade if grading else "N/A"

def calculate_weighted_subject_averages(assessments):
    if not assessments.exists():
        return []
    
    subject_scores = {}
    for result in assessments:
        subject = result.assessment.subject.name
        assessment_type = result.assessment.assessment_type
        weight = Decimal(str(result.assessment.assessment_type.weight or 1))
        raw_score = Decimal(str(result.score))
        if subject not in subject_scores:
            subject_scores[subject] = {
                'total_score': Decimal('0.0'),
                'total_weight': Decimal('0.0'),
                'assessments': [],
                'teacher': getattr(result.assessment.subject, 'teacher', None),
            }
        subject_scores[subject]['total_score'] += raw_score * weight
        subject_scores[subject]['total_weight'] += weight
        subject_scores[subject]['assessments'].append({
            'id': assessment_type.id,
            'name': assessment_type.name
        })
    
    averages = []
    for subject, data in subject_scores.items():
        average = (data['total_score'] / data['total_weight']).quantize(Decimal('0.01')) if data['total_weight'] else Decimal('0.00')
        grade, points = get_grade_and_points(average)
        unique_assessments = {a['id']: a for a in data['assessments']}.values()
        averages.append({
            'subject': subject,
            'average': float(average),
            'grade': grade,
            'points': points,
            'assessments': list(unique_assessments),
            'teacher': data['teacher'],
        })
    return averages


def get_division(total_aggregates):
    if 4 <= total_aggregates <= 12:
        return "Division 1"
    elif 13 <= total_aggregates <= 23:
        return "Division 2"
    elif 24 <= total_aggregates <= 29:
        return "Division 3"
    elif 30 <= total_aggregates <= 34:
        return "Division 4"
    else:
        return "U"  

