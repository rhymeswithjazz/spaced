def user_preferences(request):
    """Add user preferences to template context."""
    if request.user.is_authenticated:
        from .models import UserPreferences
        preferences, _ = UserPreferences.objects.get_or_create(user=request.user)
        return {
            'user_theme': preferences.theme,
        }
    return {'user_theme': 'system'}
