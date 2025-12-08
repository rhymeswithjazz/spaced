from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

from .models import Deck, Card, UserPreferences, ReviewReminder
from . import cloze


class StyledFormMixin:
    """Mixin to add Tailwind CSS classes to form fields."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            base_classes = (
                "block w-full rounded-md border-gray-300 dark:border-gray-600 "
                "bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 "
                "shadow-sm focus:border-primary-500 focus:ring-primary-500 "
                "sm:text-sm px-3 py-2"
            )
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = (
                    "h-4 w-4 rounded border-gray-300 dark:border-gray-600 "
                    "text-primary-600 focus:ring-primary-500"
                )
            elif isinstance(field.widget, forms.Select):
                # Custom select styling with SVG chevron for consistent cross-browser appearance
                select_classes = (
                    "block w-full rounded-md border-gray-300 dark:border-gray-600 "
                    "bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 "
                    "shadow-sm focus:border-primary-500 focus:ring-primary-500 "
                    "sm:text-sm px-3 py-2 pr-10 appearance-none cursor-pointer "
                    "bg-no-repeat bg-[length:1.25rem_1.25rem] bg-[position:right_0.5rem_center] "
                    "bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2020%2020%22%20fill%3D%22%236b7280%22%3E%3Cpath%20fill-rule%3D%22evenodd%22%20d%3D%22M5.23%207.21a.75.75%200%20011.06.02L10%2011.168l3.71-3.938a.75.75%200%20111.08%201.04l-4.25%204.5a.75.75%200%2001-1.08%200l-4.25-4.5a.75.75%200%2001.02-1.06z%22%20clip-rule%3D%22evenodd%22%2F%3E%3C%2Fsvg%3E')] "
                    "dark:bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2020%2020%22%20fill%3D%22%239ca3af%22%3E%3Cpath%20fill-rule%3D%22evenodd%22%20d%3D%22M5.23%207.21a.75.75%200%20011.06.02L10%2011.168l3.71-3.938a.75.75%200%20111.08%201.04l-4.25%204.5a.75.75%200%2001-1.08%200l-4.25-4.5a.75.75%200%2001.02-1.06z%22%20clip-rule%3D%22evenodd%22%2F%3E%3C%2Fsvg%3E')]"
                )
                field.widget.attrs['class'] = select_classes
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs['class'] = base_classes
                field.widget.attrs['rows'] = 3
            elif isinstance(field.widget, forms.TimeInput):
                # Add dark color-scheme for native time picker icons
                field.widget.attrs['class'] = base_classes + " dark:[color-scheme:dark]"
            elif isinstance(field.widget, forms.DateInput):
                # Add dark color-scheme for native date picker icons
                field.widget.attrs['class'] = base_classes + " dark:[color-scheme:dark]"
            else:
                field.widget.attrs['class'] = base_classes


class LoginForm(StyledFormMixin, AuthenticationForm):
    """Custom login form with styled fields."""
    pass


class RegisterForm(StyledFormMixin, UserCreationForm):
    """User registration form."""
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class DeckForm(StyledFormMixin, forms.ModelForm):
    """Form for creating and editing decks."""

    class Meta:
        model = Deck
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class CardForm(StyledFormMixin, forms.ModelForm):
    """Form for creating and editing cards."""

    class Meta:
        model = Card
        fields = ['card_type', 'front', 'back', 'notes']
        widgets = {
            'front': forms.Textarea(attrs={'rows': 3}),
            'back': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def clean(self):
        cleaned_data = super().clean()
        card_type = cleaned_data.get('card_type')
        front = cleaned_data.get('front', '')

        if card_type == Card.CardType.CLOZE:
            errors = cloze.validate_cloze_syntax(front)
            if errors:
                for error in errors:
                    self.add_error('front', error)

        return cleaned_data


class UserPreferencesForm(StyledFormMixin, forms.ModelForm):
    """Form for user preferences."""

    class Meta:
        model = UserPreferences
        fields = [
            'theme', 'card_text_size', 'cards_per_session',
            'celebration_animations',
            'email_study_reminders', 'email_streak_reminders',
            'email_weekly_stats', 'email_inactivity_nudge',
            'email_achievement_notifications', 'email_unsubscribed',
        ]


class ReviewReminderForm(StyledFormMixin, forms.ModelForm):
    """Form for review reminder settings."""

    # Day checkboxes for custom frequency
    DAY_CHOICES = [
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday'),
    ]

    custom_days_checkboxes = forms.MultipleChoiceField(
        choices=DAY_CHOICES,
        widget=forms.CheckboxSelectMultiple(),
        required=False,
        label='Days to receive reminders',
    )

    class Meta:
        model = ReviewReminder
        fields = ['enabled', 'frequency', 'preferred_time']
        widgets = {
            'preferred_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize checkboxes from existing custom_days value
        if self.instance and self.instance.custom_days:
            days = [d.strip() for d in self.instance.custom_days.split(',') if d.strip()]
            self.fields['custom_days_checkboxes'].initial = days

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Convert checkboxes back to comma-separated string
        selected_days = self.cleaned_data.get('custom_days_checkboxes', [])
        instance.custom_days = ','.join(sorted(selected_days))
        if commit:
            instance.save()
        return instance
