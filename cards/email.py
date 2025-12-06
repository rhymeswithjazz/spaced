"""Email utility functions for sending branded, themed emails."""

import os
import uuid
from email.mime.image import MIMEImage

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


# Color schemes for light and dark themes
THEME_COLORS = {
    'light': {
        'background': '#f8fafc',
        'card_background': '#ffffff',
        'primary_text': '#0f172a',
        'secondary_text': '#64748b',
        'accent': '#0284c7',
        'accent_light': '#0ea5e9',
        'button_bg': '#0ea5e9',
        'button_text': '#ffffff',
        'border': '#e2e8f0',
        'success': '#22c55e',
        'warning': '#f59e0b',
    },
    'dark': {
        'background': '#1e293b',
        'card_background': '#0f172a',
        'primary_text': '#f1f5f9',
        'secondary_text': '#94a3b8',
        'accent': '#38bdf8',
        'accent_light': '#7dd3fc',
        'button_bg': '#0ea5e9',
        'button_text': '#ffffff',
        'border': '#334155',
        'success': '#4ade80',
        'warning': '#fbbf24',
    },
}


def get_email_theme(user):
    """
    Get appropriate theme for user's emails.

    Since email clients don't reliably support prefers-color-scheme,
    we use the user's stored preference. SYSTEM defaults to light.
    """
    prefs = getattr(user, 'preferences', None)
    if prefs and prefs.theme == 'dark':
        return 'dark'
    elif prefs and prefs.theme == 'light':
        return 'light'
    # For SYSTEM preference, default to light (safer for email clients)
    return 'light'


def get_theme_colors(theme):
    """Get color dictionary for the specified theme."""
    return THEME_COLORS.get(theme, THEME_COLORS['light'])


def get_unsubscribe_urls(user, request=None):
    """
    Generate unsubscribe and preference URLs for email footer.

    Returns dict with unsubscribe_url and preferences_url.
    """
    prefs = getattr(user, 'preferences', None)
    if prefs and hasattr(prefs, 'unsubscribe_token'):
        token = str(prefs.unsubscribe_token)
    else:
        # Fallback: generate a temporary token (won't work for actual unsubscribe)
        token = str(uuid.uuid4())

    base_url = ''
    if request:
        base_url = request.build_absolute_uri('/')[:-1]  # Remove trailing slash
    elif hasattr(settings, 'SITE_URL'):
        base_url = settings.SITE_URL.rstrip('/')

    return {
        'unsubscribe_url': f'{base_url}/email/unsubscribe/{token}/',
        'preferences_url': f'{base_url}/email/preferences/{token}/',
    }


def send_branded_email(
    user,
    subject,
    template_name,
    context=None,
    request=None,
    fail_silently=False,
    force_theme=None,
):
    """
    Send a branded HTML email with plain text fallback.

    Args:
        user: User object with email address
        subject: Email subject line
        template_name: Base template name without extension (e.g., 'emails/verification')
        context: Additional template context
        request: HTTP request for building absolute URLs
        fail_silently: Whether to suppress email errors
        force_theme: Override theme ('light' or 'dark'), for testing purposes

    The function automatically:
    - Determines theme based on user preference
    - Includes theme colors in context
    - Includes unsubscribe URLs
    - Sends multipart email (HTML + plain text)
    """
    if context is None:
        context = {}

    # Get theme and colors (force_theme overrides user preference)
    theme = force_theme if force_theme in ('light', 'dark') else get_email_theme(user)
    colors = get_theme_colors(theme)

    # Get unsubscribe URLs
    unsubscribe_urls = get_unsubscribe_urls(user, request)

    # Build base URL for links
    base_url = ''
    if request:
        base_url = request.build_absolute_uri('/')[:-1]
    elif hasattr(settings, 'SITE_URL'):
        base_url = settings.SITE_URL.rstrip('/')

    # Prepare context
    email_context = {
        'user': user,
        'username': user.username,
        'theme': theme,
        'colors': colors,
        'base_url': base_url,
        'app_url': base_url,
        **unsubscribe_urls,
        **context,
    }

    # Render HTML template
    html_template = f'{template_name}.html'
    html_content = render_to_string(html_template, email_context)

    # Render plain text template
    txt_template = f'{template_name}.txt'
    try:
        text_content = render_to_string(txt_template, email_context)
    except Exception:
        # Fallback: strip HTML for plain text (basic)
        import re
        text_content = re.sub(r'<[^>]+>', '', html_content)
        text_content = re.sub(r'\s+', ' ', text_content).strip()

    # Create email
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    email.attach_alternative(html_content, 'text/html')
    email.mixed_subtype = 'related'  # Required for inline images

    # Attach logo as inline image (resized for email)
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'android-chrome-192x192.png')
    if os.path.exists(logo_path):
        from io import BytesIO
        from PIL import Image

        # Resize to 48x48 to match text height
        with Image.open(logo_path) as img:
            img = img.resize((48, 48), Image.Resampling.LANCZOS)
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            logo_data = buffer.getvalue()

        logo_image = MIMEImage(logo_data)
        logo_image.add_header('Content-ID', '<logo>')
        logo_image.add_header('Content-Disposition', 'inline', filename='logo.png')
        email.attach(logo_image)

    # Send
    return email.send(fail_silently=fail_silently)


def can_send_email(user, email_type):
    """
    Check if a specific type of email can be sent to a user.

    Args:
        user: User object
        email_type: One of 'study_reminders', 'streak_reminders',
                   'weekly_stats', 'inactivity_nudge', 'achievement_notifications'

    Returns:
        bool: True if email can be sent
    """
    prefs = getattr(user, 'preferences', None)
    if not prefs:
        return True  # Default to allowing emails

    # Check global unsubscribe
    if getattr(prefs, 'email_unsubscribed', False):
        return False

    # Check specific email type
    pref_field = f'email_{email_type}'
    return getattr(prefs, pref_field, True)
