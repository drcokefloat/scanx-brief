"""
Forms for the Brief application.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Brief


class BriefCreateForm(forms.ModelForm):
    """Form for creating a new clinical trial brief."""
    
    topic = forms.CharField(
        max_length=200,
        min_length=2,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Alzheimer\'s Disease, Oncology, Diabetes',
            'autocomplete': 'off'
        }),
        help_text='Enter a medical condition or therapeutic area to analyze clinical trials'
    )
    
    class Meta:
        model = Brief
        fields = ['topic']
    
    def clean_topic(self):
        """Validate and clean the topic field."""
        topic = self.cleaned_data.get('topic', '').strip()
        
        if not topic:
            raise ValidationError('Topic is required.')
        
        if len(topic) < 2:
            raise ValidationError('Topic must be at least 2 characters long.')
        
        # Check for common medical terms to ensure relevance
        medical_keywords = [
            'disease', 'syndrome', 'disorder', 'cancer', 'tumor', 'therapy',
            'treatment', 'drug', 'medicine', 'clinical', 'trial', 'study',
            'oncology', 'cardiology', 'neurology', 'diabetes', 'hypertension',
            'alzheimer', 'parkinson', 'covid', 'vaccine', 'immunology',
            'pharmaceutical', 'biotech', 'medical', 'health'
        ]
        
        topic_lower = topic.lower()
        if not any(keyword in topic_lower for keyword in medical_keywords):
            # Allow anyway but add warning in help text
            pass
        
        return topic
    
    def save(self, commit=True, owner=None):
        """Save the form with the owner."""
        brief = super().save(commit=False)
        if owner:
            brief.owner = owner
        if commit:
            brief.save()
        return brief


class CustomUserCreationForm(UserCreationForm):
    """Enhanced user creation form with email and better validation."""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        }),
        help_text='We\'ll use this to send you updates about your briefs'
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name (optional)'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name (optional)'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes to default fields
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Choose a username'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Create a password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })
        
        # Update help texts
        self.fields['username'].help_text = 'Letters, digits and @/./+/-/_ only.'
        self.fields['password1'].help_text = 'Must be at least 8 characters.'
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
    
    def clean_email(self):
        """Validate that email is unique."""
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise ValidationError('A user with this email already exists.')
        return email
    
    def save(self, commit=True):
        """Save the user with email."""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        if commit:
            user.save()
        return user


class BriefFilterForm(forms.Form):
    """Form for filtering briefs on the dashboard."""
    
    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    SORT_CHOICES = [
        ('-created_at', 'Newest First'),
        ('created_at', 'Oldest First'),
        ('topic', 'Topic A-Z'),
        ('-topic', 'Topic Z-A'),
    ]
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search briefs...',
            'autocomplete': 'off'
        })
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    sort = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        initial='-created_at',
        widget=forms.Select(attrs={'class': 'form-control'})
    ) 