"""
Brief models for ScanX Clinical Trial Intelligence Platform.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


class BriefQuerySet(models.QuerySet):
    """Custom queryset for Brief model."""
    
    def for_user(self, user: User):
        """Filter briefs for a specific user."""
        return self.filter(owner=user)
    
    def active(self):
        """Filter active (non-expired) briefs."""
        return self.filter(expires_at__gt=timezone.now())
    
    def with_trials(self):
        """Prefetch related trials for efficiency."""
        return self.prefetch_related('trials')


class BriefManager(models.Manager):
    """Custom manager for Brief model."""
    
    def get_queryset(self):
        return BriefQuerySet(self.model, using=self._db)
    
    def for_user(self, user: User):
        return self.get_queryset().for_user(user)
    
    def active(self):
        return self.get_queryset().active()


class Brief(models.Model):
    """
    A clinical trial brief containing analysis of trials for a specific topic.
    """
    
    # Status choices
    STATUS_GENERATING = 'generating'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    
    STATUS_CHOICES = [
        (STATUS_GENERATING, 'Generating'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
    ]
    
    # Core fields
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="Unique identifier for the brief"
    )
    topic = models.CharField(
        max_length=200,
        validators=[MinLengthValidator(2)],
        help_text="Medical condition or therapeutic area to analyze"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_GENERATING,
        help_text="Current status of the brief generation"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        help_text="When the brief was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        null=True,
        help_text="When the brief was last updated"
    )
    expires_at = models.DateTimeField(
        help_text="When the brief expires"
    )
    
    # Content
    gpt_summary = models.TextField(
        blank=True,
        help_text="AI-generated summary of the clinical trial landscape"
    )
    
    # Search transparency data
    search_metadata = models.JSONField(
        blank=True,
        null=True,
        help_text="Search methodology and transparency data for information specialists"
    )
    
    # Relationships
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='briefs',
        null=True,
        blank=True,
        help_text="User who owns this brief"
    )
    
    # Custom manager
    objects = BriefManager()
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['expires_at']),
        ]
        verbose_name = 'Clinical Brief'
        verbose_name_plural = 'Clinical Briefs'
    
    def __str__(self) -> str:
        return f"{self.topic} ({self.get_status_display()})"
    
    def get_absolute_url(self) -> str:
        """Return the URL for this brief's dashboard."""
        return reverse('brief_dashboard', kwargs={'brief_id': self.id})
    
    def save(self, *args, **kwargs):
        """Override save to set expiration date if not set."""
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self) -> bool:
        """Check if the brief has expired."""
        return timezone.now() > self.expires_at
    
    @property
    def is_completed(self) -> bool:
        """Check if the brief generation is completed."""
        return self.status == self.STATUS_COMPLETED
    
    @property
    def trial_count(self) -> int:
        """Get the total number of trials in this brief."""
        return self.trials.count()
    
    @property
    def active_trial_count(self) -> int:
        """Get the number of active/recruiting trials."""
        return self.trials.filter(
            status__icontains='recruiting'
        ).count()
    
    @property
    def phase3_trial_count(self) -> int:
        """Get the number of Phase 3 trials."""
        return self.trials.filter(phase='PHASE3').count()
    
    @property
    def unique_sponsors(self) -> list:
        """Get list of unique sponsors."""
        return list(
            self.trials.exclude(sponsor='')
            .values_list('sponsor', flat=True)
            .distinct()
        )


class TrialQuerySet(models.QuerySet):
    """Custom queryset for Trial model."""
    
    def active(self):
        """Filter active/recruiting trials."""
        return self.filter(status__icontains='recruiting')
    
    def by_phase(self, phase: str):
        """Filter trials by phase."""
        return self.filter(phase=phase)
    
    def recent(self):
        """Order by most recent start date."""
        return self.order_by('-start_date')


class Trial(models.Model):
    """
    A clinical trial record from ClinicalTrials.gov.
    """
    
    # Core identifiers
    brief = models.ForeignKey(
        Brief,
        on_delete=models.CASCADE,
        related_name="trials",
        help_text="Brief this trial belongs to"
    )
    nct_id = models.CharField(
        max_length=20,
        help_text="NCT identifier from ClinicalTrials.gov"
    )
    
    # Trial details
    title = models.CharField(
        max_length=400,
        help_text="Official trial title"
    )
    sponsor = models.CharField(
        max_length=200,
        blank=True,
        help_text="Lead sponsor organization"
    )
    phase = models.CharField(
        max_length=20,
        blank=True,
        help_text="Trial phase (e.g., PHASE1, PHASE2, etc.)"
    )
    status = models.CharField(
        max_length=50,
        blank=True,
        help_text="Current trial status"
    )
    
    # Dates
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Trial start date"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        help_text="When this record was created"
    )
    
    # External link
    url = models.URLField(
        help_text="Link to ClinicalTrials.gov page"
    )
    
    # Custom manager
    objects = TrialQuerySet.as_manager()
    
    class Meta:
        ordering = ['-start_date', 'nct_id']
        indexes = [
            models.Index(fields=['brief', '-start_date']),
            models.Index(fields=['phase']),
            models.Index(fields=['status']),
            models.Index(fields=['sponsor']),
            models.Index(fields=['nct_id']),
        ]
        verbose_name = 'Clinical Trial'
        verbose_name_plural = 'Clinical Trials'
    
    def __str__(self) -> str:
        return f"{self.nct_id}: {self.title[:50]}..."
    
    def get_absolute_url(self) -> str:
        """Return the ClinicalTrials.gov URL."""
        return self.url
    
    @property
    def is_active(self) -> bool:
        """Check if trial is actively recruiting."""
        return 'recruiting' in self.status.lower() if self.status else False
    
    @property
    def phase_display(self) -> str:
        """Get a formatted phase display."""
        if not self.phase:
            return 'N/A'
        return self.phase.replace('PHASE', 'Phase ').replace('_', '/')
    
    @property
    def sponsor_display(self) -> str:
        """Get sponsor or 'N/A' if empty."""
        return self.sponsor or 'N/A'
