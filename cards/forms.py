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
                field.widget.attrs['class'] = base_classes
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs['class'] = base_classes
                field.widget.attrs['rows'] = 3
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
        fields = ['theme', 'card_text_size', 'cards_per_session']


class ReviewReminderForm(StyledFormMixin, forms.ModelForm):
    """Form for review reminder settings."""

    class Meta:
        model = ReviewReminder
        fields = ['enabled', 'frequency', 'preferred_time', 'custom_days']
        widgets = {
            'preferred_time': forms.TimeInput(attrs={'type': 'time'}),
        }
