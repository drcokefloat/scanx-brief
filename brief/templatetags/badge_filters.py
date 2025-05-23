"""
Template filters for status badges and trial information display.
"""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def status_badge(status):
    """
    Convert status text to a Bootstrap badge with appropriate styling.
    """
    if not status:
        return mark_safe('<span class="badge badge-secondary">Unknown</span>')
    
    status_lower = status.lower()
    
    # Define status-to-class mappings
    status_classes = {
        'recruiting': 'badge-success',
        'active': 'badge-success',
        'enrolling': 'badge-success',
        'not yet recruiting': 'badge-warning',
        'suspended': 'badge-warning',
        'terminated': 'badge-danger',
        'completed': 'badge-info',
        'withdrawn': 'badge-secondary',
        'unknown': 'badge-secondary',
        'generating': 'badge-warning',
        'failed': 'badge-danger',
    }
    
    # Find matching class
    badge_class = 'badge-secondary'  # default
    for key, css_class in status_classes.items():
        if key in status_lower:
            badge_class = css_class
            break
    
    return mark_safe(f'<span class="badge {badge_class}">{status}</span>')


@register.filter
def phase_badge(phase):
    """
    Convert phase text to a styled badge.
    """
    if not phase:
        return mark_safe('<span class="badge badge-light">N/A</span>')
    
    # Clean up phase text
    phase_clean = phase.replace('PHASE', 'Phase ').replace('_', '/')
    
    # Color coding for phases
    phase_classes = {
        'phase 1': 'badge-light',
        'phase 2': 'badge-primary',
        'phase 3': 'badge-warning',
        'phase 4': 'badge-success',
        'phase 0': 'badge-secondary',
    }
    
    badge_class = 'badge-light'  # default
    for key, css_class in phase_classes.items():
        if key in phase_clean.lower():
            badge_class = css_class
            break
    
    return mark_safe(f'<span class="badge {badge_class}">{phase_clean}</span>')


@register.filter
def trial_count_badge(count):
    """
    Display trial count with appropriate badge styling.
    """
    if count == 0:
        return mark_safe('<span class="badge badge-secondary">0</span>')
    elif count < 10:
        return mark_safe(f'<span class="badge badge-primary">{count}</span>')
    elif count < 50:
        return mark_safe(f'<span class="badge badge-success">{count}</span>')
    else:
        return mark_safe(f'<span class="badge badge-warning">{count}</span>')


@register.filter
def brief_status_icon(status):
    """
    Get an icon for brief status.
    """
    if not status:
        return ""
    
    status_icons = {
        'generating': '<i class="fas fa-spinner fa-spin text-warning"></i>',
        'completed': '<i class="fas fa-check-circle text-success"></i>',
        'failed': '<i class="fas fa-exclamation-triangle text-danger"></i>',
    }
    
    return mark_safe(status_icons.get(status.lower(), ''))


@register.filter
def sponsor_short(sponsor, max_length=30):
    """
    Truncate sponsor name to a maximum length.
    """
    if not sponsor:
        return "N/A"
    
    if len(sponsor) <= max_length:
        return sponsor
    
    return f"{sponsor[:max_length-3]}..."


@register.filter
def trial_age_days(start_date):
    """
    Calculate the age of a trial in days from start date.
    """
    if not start_date:
        return None
    
    from django.utils import timezone
    import datetime
    
    if isinstance(start_date, str):
        try:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            return None
    
    if isinstance(start_date, datetime.date):
        today = timezone.now().date()
        return (today - start_date).days
    
    return None


@register.filter
def trial_age_badge(start_date):
    """
    Display trial age as a badge.
    """
    age_days = trial_age_days(start_date)
    
    if age_days is None:
        return mark_safe('<span class="badge badge-light">Unknown</span>')
    
    if age_days < 0:
        return mark_safe('<span class="badge badge-info">Future</span>')
    elif age_days < 365:
        return mark_safe(f'<span class="badge badge-success">{age_days}d old</span>')
    elif age_days < 365 * 3:
        years = age_days // 365
        return mark_safe(f'<span class="badge badge-warning">{years}y old</span>')
    else:
        years = age_days // 365
        return mark_safe(f'<span class="badge badge-secondary">{years}y old</span>')


@register.simple_tag
def progress_bar(current, total, label="Progress"):
    """
    Generate a progress bar HTML.
    """
    if total == 0:
        percentage = 0
    else:
        percentage = min(100, (current / total) * 100)
    
    return mark_safe(f'''
    <div class="progress" style="height: 20px;">
        <div class="progress-bar" role="progressbar" 
             style="width: {percentage}%" 
             aria-valuenow="{current}" 
             aria-valuemin="0" 
             aria-valuemax="{total}">
            {label}: {current}/{total}
        </div>
    </div>
    ''')


@register.filter
def dict_get(dictionary, key):
    """
    Get a value from a dictionary using a dynamic key.
    """
    if not isinstance(dictionary, dict):
        return ""
    return dictionary.get(key, "")
