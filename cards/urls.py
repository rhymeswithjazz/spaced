from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('login/', views.LoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('verification-sent/', views.verification_sent, name='verification_sent'),
    path('resend-verification/', views.ResendVerificationView.as_view(), name='resend_verification'),

    # Landing & Dashboard
    path('', views.landing, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Decks
    path('decks/', views.DeckListView.as_view(), name='deck_list'),
    path('decks/new/', views.DeckCreateView.as_view(), name='deck_create'),
    path('decks/import/', views.deck_import, name='deck_import'),
    path('decks/<int:pk>/', views.deck_detail, name='deck_detail'),
    path('decks/<int:pk>/edit/', views.DeckUpdateView.as_view(), name='deck_update'),
    path('decks/<int:pk>/delete/', views.DeckDeleteView.as_view(), name='deck_delete'),
    path('decks/<int:pk>/export/', views.deck_export, name='deck_export'),
    path('decks/<int:pk>/reset/', views.deck_reset, name='deck_reset'),

    # Cards
    path('decks/<int:deck_pk>/cards/new/', views.CardCreateView.as_view(), name='card_create'),
    path('cards/<int:pk>/edit/', views.CardUpdateView.as_view(), name='card_update'),
    path('cards/<int:pk>/delete/', views.CardDeleteView.as_view(), name='card_delete'),

    # Review
    path('review/', views.review_session, name='review_session'),
    path('review/deck/<int:deck_pk>/', views.review_session, name='review_deck'),
    path('review/struggling/', views.review_struggling, name='review_struggling'),
    path('api/review/<int:pk>/', views.review_card, name='review_card'),

    # Practice mode (review cards early without affecting SRS)
    path('review/practice/', views.practice_session, name='practice_session'),
    path('review/practice/<int:deck_pk>/', views.practice_session, name='practice_session_deck'),
    path('api/practice/<int:pk>/', views.practice_card, name='practice_card'),

    # Settings
    path('settings/', views.settings_view, name='settings'),

    # API
    path('api/theme/', views.api_set_theme, name='api_set_theme'),
    path('api/theme/get/', views.api_get_theme, name='api_get_theme'),

    # Email preferences (no login required - uses token)
    path('email/unsubscribe/<uuid:token>/', views.unsubscribe, name='email_unsubscribe'),
    path('email/unsubscribe/<uuid:token>/<str:email_type>/', views.unsubscribe_type, name='email_unsubscribe_type'),
    path('email/preferences/<uuid:token>/', views.manage_preferences, name='email_preferences'),

    # Email preview (staff only, DEBUG mode only)
    path('email/preview/<str:email_type>/', views.preview_email, name='email_preview'),

    # Health check
    path('health/', views.health_check, name='health_check'),
]
