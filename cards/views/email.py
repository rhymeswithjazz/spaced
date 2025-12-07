"""Email unsubscribe and preference management views."""

from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods

from ..models import UserPreferences
from ..email import get_theme_colors


def get_preferences_by_token(token):
    """Get UserPreferences by unsubscribe token."""
    return get_object_or_404(UserPreferences, unsubscribe_token=token)


def unsubscribe(request, token):
    """One-click unsubscribe from all emails."""
    prefs = get_preferences_by_token(token)

    if request.method == 'POST':
        prefs.email_unsubscribed = True
        prefs.save()
        return render(request, 'cards/email/unsubscribed.html', {
            'username': prefs.user.username,
            'resubscribe_url': f'/email/preferences/{token}/',
        })

    return render(request, 'cards/email/unsubscribe_confirm.html', {
        'username': prefs.user.username,
        'token': token,
    })


def unsubscribe_type(request, token, email_type):
    """Unsubscribe from a specific email type."""
    prefs = get_preferences_by_token(token)

    email_type_fields = {
        'study_reminders': 'email_study_reminders',
        'streak_reminders': 'email_streak_reminders',
        'weekly_stats': 'email_weekly_stats',
        'inactivity_nudge': 'email_inactivity_nudge',
        'achievement': 'email_achievement_notifications',
    }

    email_type_labels = {
        'study_reminders': 'Study Reminders',
        'streak_reminders': 'Streak Reminders',
        'weekly_stats': 'Weekly Statistics',
        'inactivity_nudge': 'Inactivity Nudges',
        'achievement': 'Achievement Notifications',
    }

    if email_type not in email_type_fields:
        return redirect('email_preferences', token=token)

    field_name = email_type_fields[email_type]
    label = email_type_labels[email_type]

    if request.method == 'POST':
        setattr(prefs, field_name, False)
        prefs.save()
        return render(request, 'cards/email/unsubscribed_type.html', {
            'username': prefs.user.username,
            'email_type_label': label,
            'preferences_url': f'/email/preferences/{token}/',
        })

    return render(request, 'cards/email/unsubscribe_type_confirm.html', {
        'username': prefs.user.username,
        'email_type': email_type,
        'email_type_label': label,
        'token': token,
    })


@require_http_methods(['GET', 'POST'])
def manage_preferences(request, token):
    """Email preference management page (no login required)."""
    prefs = get_preferences_by_token(token)

    email_types = [
        {
            'field': 'email_study_reminders',
            'label': 'Study Reminders',
            'description': 'Daily reminders when you have cards due for review',
        },
        {
            'field': 'email_streak_reminders',
            'label': 'Streak Alerts',
            'description': 'Get notified when your streak is at risk',
        },
        {
            'field': 'email_weekly_stats',
            'label': 'Weekly Progress Report',
            'description': 'Sunday summary of your learning progress',
        },
        {
            'field': 'email_inactivity_nudge',
            'label': 'Come Back Nudges',
            'description': 'Friendly reminders if you haven\'t studied in a few days',
        },
        {
            'field': 'email_achievement_notifications',
            'label': 'Achievement Celebrations',
            'description': 'Get notified when you hit milestones',
        },
    ]

    if request.method == 'POST':
        # Check if this is a global unsubscribe/resubscribe
        if 'unsubscribe_all' in request.POST:
            prefs.email_unsubscribed = True
            prefs.save()
            messages.success(request, 'You have been unsubscribed from all emails.')
        elif 'resubscribe' in request.POST:
            prefs.email_unsubscribed = False
            prefs.save()
            messages.success(request, 'You have been resubscribed to emails.')
        else:
            # Update individual preferences
            for email_type in email_types:
                field = email_type['field']
                value = request.POST.get(field) == 'on'
                setattr(prefs, field, value)
            prefs.save()
            messages.success(request, 'Your email preferences have been updated.')

        return redirect('email_preferences', token=token)

    # Add current values to email_types
    for email_type in email_types:
        email_type['enabled'] = getattr(prefs, email_type['field'])

    return render(request, 'cards/email/preferences.html', {
        'username': prefs.user.username,
        'email_types': email_types,
        'email_unsubscribed': prefs.email_unsubscribed,
        'token': token,
    })


@staff_member_required
def preview_email(request, email_type):
    """
    Preview email templates in the browser.

    Only available to staff members for security.
    Access at: /email/preview/<email_type>/?theme=light|dark
    """
    if not settings.DEBUG:
        raise Http404("Email preview only available in DEBUG mode")

    # Get theme from query param, default to light
    theme = request.GET.get('theme', 'light')
    if theme not in ('light', 'dark'):
        theme = 'light'

    colors = get_theme_colors(theme)
    base_url = request.build_absolute_uri('/')[:-1]

    # Build context based on email type
    base_context = {
        'username': request.user.username,
        'user': request.user,
        'theme': theme,
        'colors': colors,
        'base_url': base_url,
        'app_url': base_url,
        'unsubscribe_url': f'{base_url}/email/unsubscribe/test-token/',
        'preferences_url': f'{base_url}/email/preferences/test-token/',
    }

    templates = {
        'study_reminder': {
            'template': 'emails/study_reminder.html',
            'context': {
                'due_count': 15,
                'review_url': f'{base_url}/review/',
                'current_streak': 5,
                'total_reviews': 342,
            },
        },
        'streak_reminder': {
            'template': 'emails/streak_reminder.html',
            'context': {
                'current_streak': 12,
                'hours_remaining': 6,
                'review_url': f'{base_url}/review/',
            },
        },
        'weekly_stats': {
            'template': 'emails/weekly_stats.html',
            'context': {
                'cards_reviewed_this_week': 87,
                'cards_reviewed_last_week': 62,
                'review_change_percent': 40,
                'review_change_direction': 'up',
                'current_streak': 14,
                'longest_streak': 21,
                'total_cards': 250,
                'mature_cards': 85,
                'learning_cards': 120,
                'new_cards': 45,
                'review_url': f'{base_url}/review/',
            },
        },
        'inactivity_nudge': {
            'template': 'emails/inactivity_nudge.html',
            'context': {
                'days_inactive': 5,
                'cards_waiting': 42,
                'review_url': f'{base_url}/review/',
            },
        },
        'achievement': {
            'template': 'emails/achievement.html',
            'context': {
                'achievement_title': '7-Day Streak',
                'achievement_description': "A full week of consistent study! You're building great habits.",
                'achievement_emoji': '🔥',
                'achievement_stat': 7,
                'achievement_stat_label': 'day streak',
                'review_url': f'{base_url}/review/',
            },
        },
        'verification': {
            'template': 'emails/verification.html',
            'context': {
                'verification_url': f'{base_url}/verify-email/test-token/',
                'hours_valid': 24,
            },
        },
    }

    if email_type not in templates:
        available = ', '.join(templates.keys())
        return HttpResponse(
            f'<h1>Unknown email type: {email_type}</h1>'
            f'<p>Available types: {available}</p>'
            f'<p>Add ?theme=dark to preview dark mode</p>',
            content_type='text/html'
        )

    template_info = templates[email_type]
    context = {**base_context, **template_info['context']}

    html_content = render_to_string(template_info['template'], context)

    # Add a preview toolbar at the top
    toolbar = f'''
    <div style="position:fixed;top:0;left:0;right:0;background:#1e293b;color:white;padding:8px 16px;font-family:system-ui;font-size:14px;z-index:9999;display:flex;gap:16px;align-items:center;">
        <strong>Email Preview:</strong>
        <span>{email_type}</span>
        <span>|</span>
        <a href="?theme=light" style="color:{'#38bdf8' if theme == 'light' else '#94a3b8'};">Light</a>
        <a href="?theme=dark" style="color:{'#38bdf8' if theme == 'dark' else '#94a3b8'};">Dark</a>
        <span>|</span>
        {''.join(f'<a href="/email/preview/{t}/?theme={theme}" style="color:#94a3b8;">{t}</a>' for t in templates.keys())}
    </div>
    <div style="height:50px;"></div>
    '''

    return HttpResponse(toolbar + html_content, content_type='text/html')
