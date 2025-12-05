"""Settings and API views."""

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from ..models import ReviewReminder
from ..forms import UserPreferencesForm, ReviewReminderForm
from .helpers import get_or_create_preferences


@login_required
def settings_view(request):
    """User settings page."""
    user = request.user
    preferences = get_or_create_preferences(user)
    reminder, _ = ReviewReminder.objects.get_or_create(user=user)

    if request.method == 'POST':
        pref_form = UserPreferencesForm(request.POST, instance=preferences)
        reminder_form = ReviewReminderForm(request.POST, instance=reminder)

        if pref_form.is_valid() and reminder_form.is_valid():
            pref_form.save()
            reminder_form.save()
            messages.success(request, 'Settings saved!')
            return redirect('settings')
    else:
        pref_form = UserPreferencesForm(instance=preferences)
        reminder_form = ReviewReminderForm(instance=reminder)

    context = {
        'pref_form': pref_form,
        'reminder_form': reminder_form,
    }
    return render(request, 'cards/settings.html', context)


@login_required
@require_POST
def api_set_theme(request):
    """API endpoint to sync theme preference to database."""
    try:
        data = json.loads(request.body)
        theme = data.get('theme', 'system')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if theme not in ['light', 'dark', 'system']:
        return JsonResponse({'error': 'Invalid theme'}, status=400)

    preferences = get_or_create_preferences(request.user)
    preferences.theme = theme
    preferences.save()

    return JsonResponse({'success': True, 'theme': theme})


@login_required
def api_get_theme(request):
    """API endpoint to get user's theme preference."""
    preferences = get_or_create_preferences(request.user)
    return JsonResponse({'theme': preferences.theme})
