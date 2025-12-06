"""Views package for the cards app."""

from .auth import (
    LoginView,
    RegisterView,
    logout_view,
    verification_sent,
    verify_email,
    ResendVerificationView,
)
from .dashboard import dashboard
from .landing import landing
from .deck import (
    DeckListView,
    DeckCreateView,
    DeckUpdateView,
    DeckDeleteView,
    deck_detail,
    deck_export,
    deck_import,
    deck_reset,
)
from .card import CardCreateView, CardUpdateView, CardDeleteView
from .review import review_session, review_card
from .settings import settings_view, api_set_theme, api_get_theme
from .email import unsubscribe, unsubscribe_type, manage_preferences, preview_email
from .health import health_check

__all__ = [
    # Auth
    'LoginView',
    'RegisterView',
    'logout_view',
    'verification_sent',
    'verify_email',
    'ResendVerificationView',
    # Dashboard
    'dashboard',
    # Landing
    'landing',
    # Deck
    'DeckListView',
    'DeckCreateView',
    'DeckUpdateView',
    'DeckDeleteView',
    'deck_detail',
    'deck_export',
    'deck_import',
    'deck_reset',
    # Card
    'CardCreateView',
    'CardUpdateView',
    'CardDeleteView',
    # Review
    'review_session',
    'review_card',
    # Settings
    'settings_view',
    'api_set_theme',
    'api_get_theme',
    # Email
    'unsubscribe',
    'unsubscribe_type',
    'manage_preferences',
    'preview_email',
    # Health
    'health_check',
]
