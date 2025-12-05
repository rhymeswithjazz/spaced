from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('login/', views.LoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Decks
    path('decks/', views.DeckListView.as_view(), name='deck_list'),
    path('decks/new/', views.DeckCreateView.as_view(), name='deck_create'),
    path('decks/import/', views.deck_import, name='deck_import'),
    path('decks/<int:pk>/', views.deck_detail, name='deck_detail'),
    path('decks/<int:pk>/edit/', views.DeckUpdateView.as_view(), name='deck_update'),
    path('decks/<int:pk>/delete/', views.DeckDeleteView.as_view(), name='deck_delete'),
    path('decks/<int:pk>/export/', views.deck_export, name='deck_export'),

    # Cards
    path('decks/<int:deck_pk>/cards/new/', views.CardCreateView.as_view(), name='card_create'),
    path('cards/<int:pk>/edit/', views.CardUpdateView.as_view(), name='card_update'),
    path('cards/<int:pk>/delete/', views.CardDeleteView.as_view(), name='card_delete'),

    # Review
    path('review/', views.review_session, name='review_session'),
    path('review/deck/<int:deck_pk>/', views.review_session, name='review_deck'),
    path('api/review/<int:pk>/', views.review_card, name='review_card'),

    # Settings
    path('settings/', views.settings_view, name='settings'),

    # API
    path('api/theme/', views.api_set_theme, name='api_set_theme'),
    path('api/theme/get/', views.api_get_theme, name='api_get_theme'),
]
