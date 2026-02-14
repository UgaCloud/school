from django import template
from app.models.results import ResultBatch

register = template.Library()

@register.simple_tag
def pending_verification_count():
    """Returns the count of ResultBatch items with status 'PENDING'."""
    return ResultBatch.objects.filter(status='PENDING').count()

@register.simple_tag
def get_pending_verifications(limit=5):
    """Returns a list of pending verifications."""
    return ResultBatch.objects.filter(status='PENDING').order_by('-submitted_at')[:limit]
