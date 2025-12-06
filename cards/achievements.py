"""Achievement system for tracking and celebrating user milestones."""

from django.conf import settings
from django.db.models import Count

from .models import ReviewLog, EmailLog
from .email import send_branded_email, can_send_email


# Achievement definitions
ACHIEVEMENTS = {
    'first_review': {
        'title': 'First Step',
        'description': 'You reviewed your first flashcard! This is the beginning of your learning journey.',
        'emoji': '&#127775;',  # Star
        'stat_label': 'cards reviewed',
        'threshold': 1,
    },
    'reviews_100': {
        'title': '100 Cards Reviewed',
        'description': 'You\'ve reviewed 100 cards! Your dedication to learning is impressive.',
        'emoji': '&#127942;',  # Trophy
        'stat_label': 'cards reviewed',
        'threshold': 100,
    },
    'reviews_500': {
        'title': '500 Cards Reviewed',
        'description': 'Half a thousand cards reviewed! You\'re becoming a learning machine.',
        'emoji': '&#128170;',  # Flexed biceps
        'stat_label': 'cards reviewed',
        'threshold': 500,
    },
    'reviews_1000': {
        'title': '1,000 Cards Reviewed',
        'description': 'One thousand cards! You\'re a true knowledge seeker.',
        'emoji': '&#128293;',  # Fire
        'stat_label': 'cards reviewed',
        'threshold': 1000,
    },
    'streak_7': {
        'title': '7-Day Streak',
        'description': 'A full week of consistent study! You\'re building great habits.',
        'emoji': '&#128293;',  # Fire
        'stat_label': 'day streak',
        'threshold': 7,
    },
    'streak_30': {
        'title': '30-Day Streak',
        'description': 'A month of daily learning! Your consistency is remarkable.',
        'emoji': '&#127775;',  # Star
        'stat_label': 'day streak',
        'threshold': 30,
    },
    'streak_100': {
        'title': '100-Day Streak',
        'description': '100 days of unbroken learning! You\'re an inspiration.',
        'emoji': '&#127942;',  # Trophy
        'stat_label': 'day streak',
        'threshold': 100,
    },
}


def check_and_send_achievements(user):
    """
    Check if user has earned any new achievements and send emails.

    Should be called after a review session or when streak updates.
    Returns list of achievement keys that were awarded.
    """
    if not can_send_email(user, 'achievement_notifications'):
        return []

    prefs = getattr(user, 'preferences', None)
    if not prefs:
        return []

    awarded = []

    # Get user's total review count
    total_reviews = ReviewLog.objects.filter(card__deck__owner=user).count()

    # Check review count achievements
    review_achievements = [
        ('first_review', 1),
        ('reviews_100', 100),
        ('reviews_500', 500),
        ('reviews_1000', 1000),
    ]

    for key, threshold in review_achievements:
        if total_reviews >= threshold:
            if _award_achievement_if_new(user, key, threshold):
                awarded.append(key)

    # Check streak achievements
    streak = prefs.current_streak
    streak_achievements = [
        ('streak_7', 7),
        ('streak_30', 30),
        ('streak_100', 100),
    ]

    for key, threshold in streak_achievements:
        if streak >= threshold:
            if _award_achievement_if_new(user, key, threshold):
                awarded.append(key)

    return awarded


def _award_achievement_if_new(user, achievement_key, stat_value):
    """
    Send achievement email if this achievement hasn't been sent before.

    Returns True if achievement was awarded, False if already awarded.
    """
    achievement = ACHIEVEMENTS.get(achievement_key)
    if not achievement:
        return False

    # Check if this achievement email was already sent
    subject_pattern = achievement['title']
    already_sent = EmailLog.objects.filter(
        user=user,
        email_type=EmailLog.EmailType.ACHIEVEMENT,
        subject__contains=subject_pattern,
    ).exists()

    if already_sent:
        return False

    # Send achievement email
    _send_achievement_email(user, achievement, stat_value)
    return True


def _send_achievement_email(user, achievement, stat_value):
    """Send an achievement notification email."""
    subject = f"Achievement Unlocked: {achievement['title']}"

    # Build review URL
    base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000').rstrip('/')
    review_url = f'{base_url}/review/'

    context = {
        'achievement_title': achievement['title'],
        'achievement_description': achievement['description'],
        'achievement_emoji': achievement['emoji'],
        'achievement_stat': stat_value,
        'achievement_stat_label': achievement['stat_label'],
        'review_url': review_url,
    }

    send_branded_email(
        user=user,
        subject=subject,
        template_name='emails/achievement',
        context=context,
        fail_silently=True,  # Don't fail the review if email fails
    )

    # Log the email
    EmailLog.objects.create(
        user=user,
        email_type=EmailLog.EmailType.ACHIEVEMENT,
        subject=subject,
    )
