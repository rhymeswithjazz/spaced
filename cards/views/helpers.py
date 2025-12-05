"""Shared helper functions for views."""

from ..models import UserPreferences


def get_or_create_preferences(user):
    """Get or create user preferences."""
    preferences, _ = UserPreferences.objects.get_or_create(user=user)
    return preferences
