"""
Views for the Brief application.
"""

import logging
from typing import Any, Dict

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView, ListView

from .forms import BriefCreateForm, BriefFilterForm, CustomUserCreationForm
from .models import Brief, Trial
from .utils import generate_brief

logger = logging.getLogger(__name__)


class BriefListView(ListView):
    """Class-based view for listing user's briefs."""
    
    model = Brief
    template_name = 'brief/brief_list.html'
    context_object_name = 'briefs'
    paginate_by = 12
    
    def get_queryset(self):
        """Get briefs for the current user with filtering."""
        if not self.request.user.is_authenticated:
            return Brief.objects.none()
        
        queryset = Brief.objects.for_user(self.request.user).with_trials()
        
        # Apply filters from form
        form = BriefFilterForm(self.request.GET)
        if form.is_valid():
            search = form.cleaned_data.get('search')
            status = form.cleaned_data.get('status')
            sort = form.cleaned_data.get('sort', '-created_at')
            
            if search:
                queryset = queryset.filter(
                    Q(topic__icontains=search) | 
                    Q(gpt_summary__icontains=search)
                )
            
            if status:
                queryset = queryset.filter(status=status)
            
            if sort:
                queryset = queryset.order_by(sort)
        
        return queryset
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Add filter form to context."""
        context = super().get_context_data(**kwargs)
        context['filter_form'] = BriefFilterForm(self.request.GET)
        context['total_briefs'] = Brief.objects.for_user(self.request.user).count()
        return context


# Function-based view for backwards compatibility
@login_required
def brief_list(request: HttpRequest) -> HttpResponse:
    """Function-based wrapper for BriefListView."""
    view = BriefListView.as_view()
    return view(request)


def parse_gpt_summary(summary: str) -> list:
    """
    Parse the GPT summary into structured sections for Bootstrap display.
    """
    if not summary:
        return []
    
    sections = []
    lines = summary.split('\n')
    current_section = None
    current_content = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this is a heading (numbered sections like "1. Title" or just "Title")
        if (line and 
            (line[0].isdigit() and '. ' in line[:10]) or  # "1. Market Overview"
            (len(line) < 100 and line.endswith(':') == False and  # Not too long, not ending with ':'
             any(keyword in line.lower() for keyword in ['overview', 'activity', 'patterns', 'signals', 'intelligence', 'considerations', 'conclusion']))):
            
            # Save previous section if exists
            if current_section and current_content:
                sections.append({
                    'title': current_section,
                    'content': ' '.join(current_content).strip()
                })
            
            # Start new section
            current_section = line.replace(': ', '').replace(':', '').strip()
            current_content = []
        else:
            # Add to current content
            if line and current_section:
                current_content.append(line)
    
    # Add the last section
    if current_section and current_content:
        sections.append({
            'title': current_section,
            'content': ' '.join(current_content).strip()
        })
    
    return sections


@login_required
def brief_dashboard(request: HttpRequest, brief_id: str) -> HttpResponse:
    """
    Display the dashboard for a specific brief with trials and analysis.
    """
    try:
        brief = get_object_or_404(
            Brief.objects.select_related('owner').prefetch_related('trials'),
            id=brief_id
        )
        
        # Check permissions
        if brief.owner != request.user:
            logger.warning(
                f"User {request.user.username} attempted to access brief {brief_id} "
                f"owned by {brief.owner.username}"
            )
            raise PermissionDenied("You do not have permission to view this brief.")
        
        # Get trials with optimized queries
        trials = brief.trials.all().order_by('-start_date', 'nct_id')
        
        # Generate statistics
        trial_stats = {
            'total': trials.count(),
            'active': trials.filter(status__icontains='recruiting').count(),
            'phase1': trials.filter(phase='PHASE1').count(),
            'phase2': trials.filter(phase='PHASE2').count(),
            'phase3': trials.filter(phase='PHASE3').count(),
            'phase4': trials.filter(phase='PHASE4').count(),
        }
        
        # Get unique values for filters
        phases = sorted(set(t.phase or "N/A" for t in trials))
        statuses = sorted(set(t.status or "N/A" for t in trials))
        sponsors = sorted(set(t.sponsor or "N/A" for t in trials if t.sponsor))[:20]  # Top 20
        
        # Parse GPT summary into structured sections
        summary_sections = parse_gpt_summary(brief.gpt_summary or "")
        
        context = {
            'brief': brief,
            'trials': trials,
            'trial_stats': trial_stats,
            'phases': phases,
            'statuses': statuses,
            'sponsors': sponsors,
            'summary_sections': summary_sections,
        }
        
        logger.info(f"Brief dashboard accessed: {brief_id} by {request.user.username}")
        return render(request, 'brief/dashboard.html', context)
        
    except Brief.DoesNotExist:
        logger.error(f"Brief not found: {brief_id}")
        messages.error(request, "Brief not found.")
        return redirect('brief_list')
    except Exception as e:
        logger.error(f"Error accessing brief dashboard {brief_id}: {str(e)}")
        messages.error(request, "An error occurred while loading the brief.")
        return redirect('brief_list')


@login_required
@require_http_methods(["GET", "POST"])
def create_brief(request: HttpRequest) -> HttpResponse:
    """
    Create a new clinical trial brief.
    """
    if request.method == 'POST':
        form = BriefCreateForm(request.POST)
        
        if form.is_valid():
            try:
                topic = form.cleaned_data['topic']
                logger.info(f"Creating brief for topic: {topic} by {request.user.username}")
                
                # Create brief asynchronously (in a real app, use Celery)
                brief = generate_brief(topic, owner=request.user)
                
                logger.info(f"Brief created successfully: {brief.id}")
                
                # Redirect to dashboard without the loading message since we show it on create page
                return redirect('brief_dashboard', brief_id=brief.id)
                
            except Exception as e:
                logger.error(f"Error creating brief for {topic}: {str(e)}")
                messages.error(
                    request, 
                    "An error occurred while creating your brief. Please try again."
                )
                form.add_error(None, "Failed to create brief. Please try again.")
        else:
            logger.warning(f"Invalid brief creation form: {form.errors}")
    else:
        form = BriefCreateForm()
    
    return render(request, 'brief/create.html', {'form': form})


def signup(request: HttpRequest) -> HttpResponse:
    """
    User registration view with enhanced form.
    """
    if request.user.is_authenticated:
        return redirect('brief_list')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        
        if form.is_valid():
            try:
                user = form.save()
                logger.info(f"New user registered: {user.username}")
                
                # Log the user in immediately
                login(request, user)
                messages.success(
                    request, 
                    f"Welcome to ScanX, {user.get_full_name() or user.username}! "
                    "You can now create your first clinical trial brief."
                )
                
                return redirect('brief_list')
                
            except Exception as e:
                logger.error(f"Error during user registration: {str(e)}")
                messages.error(request, "An error occurred during registration. Please try again.")
                form.add_error(None, "Registration failed. Please try again.")
        else:
            logger.warning(f"Invalid signup form: {form.errors}")
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/signup.html', {'form': form})


@login_required
def brief_status(request: HttpRequest, brief_id: str) -> JsonResponse:
    """
    AJAX endpoint to check brief generation status.
    """
    try:
        brief = get_object_or_404(Brief, id=brief_id, owner=request.user)
        
        data = {
            'status': brief.status,
            'is_completed': brief.is_completed,
            'trial_count': brief.trial_count,
            'updated_at': brief.updated_at.isoformat(),
        }
        
        if brief.is_completed and brief.gpt_summary:
            data['has_summary'] = True
        
        return JsonResponse(data)
        
    except Brief.DoesNotExist:
        return JsonResponse({'error': 'Brief not found'}, status=404)
    except Exception as e:
        logger.error(f"Error checking brief status {brief_id}: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
def delete_brief(request: HttpRequest, brief_id: str) -> HttpResponse:
    """
    Delete a brief (POST only for security).
    """
    if request.method != 'POST':
        return redirect('brief_list')
    
    try:
        brief = get_object_or_404(Brief, id=brief_id, owner=request.user)
        topic = brief.topic
        
        brief.delete()
        logger.info(f"Brief deleted: {brief_id} ({topic}) by {request.user.username}")
        
        messages.success(request, f"Brief for '{topic}' has been deleted.")
        
    except Brief.DoesNotExist:
        messages.error(request, "Brief not found.")
    except Exception as e:
        logger.error(f"Error deleting brief {brief_id}: {str(e)}")
        messages.error(request, "An error occurred while deleting the brief.")
    
    return redirect('brief_list')


def landing_page(request: HttpRequest) -> HttpResponse:
    """
    Landing page with different content for authenticated/anonymous users.
    """
    context = {}
    
    if request.user.is_authenticated:
        # Show recent briefs for authenticated users
        recent_briefs = Brief.objects.for_user(request.user)[:3]
        context['recent_briefs'] = recent_briefs
        context['total_briefs'] = Brief.objects.for_user(request.user).count()
    
    return render(request, 'landing.html', context)



