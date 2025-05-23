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
from .utils import generate_brief, refresh_brief

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
    # Temporarily return empty list to force fallback to raw display
    return []


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
                # Get the effective search term (processed by form)
                search_term = form.cleaned_data['effective_search']
                topic = form.cleaned_data['topic']
                search_mode = form.cleaned_data['search_mode']
                
                logger.info(f"Creating brief for topic: {topic} (search: {search_term}, mode: {search_mode}) by {request.user.username}")
                
                # Create brief asynchronously (in a real app, use Celery)
                # Pass the effective search term to the generation function
                brief = generate_brief(search_term, owner=request.user, display_topic=topic)
                
                logger.info(f"Brief created successfully: {brief.id}")
                
                # Redirect to dashboard
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


@require_http_methods(["POST"])
@login_required
def delete_brief(request: HttpRequest, brief_id: str) -> HttpResponse:
    """Delete a brief."""
    brief = get_object_or_404(Brief, id=brief_id, owner=request.user)
    brief.delete()
    messages.success(request, f'Brief "{brief.topic}" deleted successfully.')
    return redirect('brief_list')


@require_http_methods(["POST"])
@login_required
def refresh_brief_view(request: HttpRequest, brief_id: str) -> HttpResponse:
    """Refresh a brief with updated data."""
    brief = get_object_or_404(Brief, id=brief_id, owner=request.user)
    
    if not brief.can_be_refreshed():
        messages.error(request, f'Brief cannot be refreshed (status: {brief.get_status_display()})')
        return redirect('brief_dashboard', brief_id=brief.id)
    
    try:
        # Refresh the brief with new data
        refresh_brief(brief)
        messages.success(request, f'Brief "{brief.topic}" refreshed successfully with latest data.')
    except Exception as e:
        logger.error(f"Failed to refresh brief {brief_id}: {str(e)}")
        messages.error(request, f'Failed to refresh brief: {str(e)}')
    
    return redirect('brief_dashboard', brief_id=brief.id)


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



