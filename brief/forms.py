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
    
    # Simple mode field (default)
    topic = forms.CharField(
        max_length=200,
        min_length=2,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g., Alzheimer\'s Disease, Oncology, Diabetes',
            'autocomplete': 'off'
        }),
        help_text='Enter a medical condition or therapeutic area to analyze clinical trials'
    )
    
    # Advanced mode fields
    search_mode = forms.ChoiceField(
        choices=[
            ('simple', 'Simple Search'),
            ('advanced', 'Advanced Search')
        ],
        initial='simple',
        required=False,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    condition = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Alzheimer\'s Disease, Type 2 Diabetes, Breast Cancer',
            'autocomplete': 'off'
        }),
        help_text='Medical condition, disease, or syndrome'
    )
    
    intervention = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Donepezil, Immunotherapy, CAR-T Cell Therapy',
            'autocomplete': 'off'
        }),
        help_text='Drug, therapy, device, or intervention being studied'
    )
    
    search_operator = forms.ChoiceField(
        choices=[
            ('AND', 'AND (both condition AND intervention)'),
            ('OR', 'OR (either condition OR intervention)'),
        ],
        initial='AND',
        required=False,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    include_observational = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Include observational studies (not just interventional trials)'
    )
    
    class Meta:
        model = Brief
        fields = ['topic']
    
    def clean(self):
        """Validate the form based on search mode."""
        cleaned_data = super().clean()
        search_mode = cleaned_data.get('search_mode', 'simple')
        topic = cleaned_data.get('topic', '').strip()
        condition = cleaned_data.get('condition', '').strip()
        intervention = cleaned_data.get('intervention', '').strip()
        
        if search_mode == 'simple':
            if not topic:
                raise ValidationError('Topic is required for simple search.')
            # Build the combined search string for backend
            cleaned_data['effective_search'] = topic
            
        else:  # advanced mode
            if not condition and not intervention:
                raise ValidationError('At least one of Condition or Intervention is required for advanced search.')
            
            # Build the search string based on operator
            search_parts = []
            if condition:
                search_parts.append(condition)
            if intervention:
                search_parts.append(intervention)
            
            operator = cleaned_data.get('search_operator', 'AND')
            if len(search_parts) == 1:
                cleaned_data['effective_search'] = search_parts[0]
            else:
                cleaned_data['effective_search'] = f' {operator} '.join(search_parts)
            
            # Set topic for the model (display purposes)
            if condition and intervention:
                cleaned_data['topic'] = f"{condition} + {intervention}"
            else:
                cleaned_data['topic'] = condition or intervention
        
        return cleaned_data
    
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