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
from .deck import (
    DeckListView,
    DeckCreateView,
    DeckUpdateView,
    DeckDeleteView,
    deck_detail,
    deck_export,
    deck_import,
)
from .card import CardCreateView, CardUpdateView, CardDeleteView
from .review import review_session, review_card
from .settings import settings_view, api_set_theme, api_get_theme

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
    # Deck
    'DeckListView',
    'DeckCreateView',
    'DeckUpdateView',
    'DeckDeleteView',
    'deck_detail',
    'deck_export',
    'deck_import',
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
]
