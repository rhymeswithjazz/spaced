"""Send test emails to preview templates."""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from cards.email import send_branded_email, get_theme_colors
from cards.models import ReviewLog, Deck, Card


class Command(BaseCommand):
    help = 'Send a test email to preview templates'

    EMAIL_TYPES = [
        'study_reminder',
        'streak_reminder',
        'weekly_stats',
        'inactivity_nudge',
        'achievement',
        'verification',
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            'username',
            help='Username to send the test email to',
        )
        parser.add_argument(
            'email_type',
            choices=self.EMAIL_TYPES,
            help=f'Type of email to send: {", ".join(self.EMAIL_TYPES)}',
        )
        parser.add_argument(
            '--theme',
            choices=['light', 'dark'],
            default=None,
            help='Force a specific theme (overrides user preference)',
        )

    def handle(self, *args, **options):
        username = options['username']
        email_type = options['email_type']
        forced_theme = options.get('theme')

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User "{username}" does not exist')

        if not user.email:
            raise CommandError(f'User "{username}" has no email address set')

        # Build context based on email type
        base_url = 'http://localhost:8000'
        context = self._build_context(user, email_type, base_url)

        # Get template and subject
        template_name, subject = self._get_template_info(email_type)

        self.stdout.write(f'Sending {email_type} email to {user.email}...')

        send_branded_email(
            user=user,
            subject=f'[TEST] {subject}',
            template_name=template_name,
            context=context,
            force_theme=forced_theme,
        )

        self.stdout.write(self.style.SUCCESS(
            f'Successfully sent {email_type} email to {user.email}'
        ))

        # If using console backend, remind user
        self.stdout.write(self.style.NOTICE(
            '\nNote: If using console email backend, check the terminal output above for the email content.'
        ))
        self.stdout.write(self.style.NOTICE(
            'To see formatted HTML, set EMAIL_BACKEND to a real SMTP server or use a tool like Mailhog.'
        ))

    def _build_context(self, user, email_type, base_url):
        """Build context dict for each email type."""

        if email_type == 'study_reminder':
            return {
                'due_count': 15,
                'review_url': f'{base_url}/review/',
                'current_streak': 5,
                'total_reviews': 342,
            }

        elif email_type == 'streak_reminder':
            return {
                'current_streak': 12,
                'hours_remaining': 6,
                'review_url': f'{base_url}/review/',
            }

        elif email_type == 'weekly_stats':
            return {
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
            }

        elif email_type == 'inactivity_nudge':
            return {
                'days_inactive': 5,
                'cards_waiting': 42,
                'review_url': f'{base_url}/review/',
            }

        elif email_type == 'achievement':
            return {
                'achievement_title': '7-Day Streak',
                'achievement_description': "A full week of consistent study! You're building great habits.",
                'achievement_emoji': '&#128293;',  # Fire emoji
                'achievement_stat': 7,
                'achievement_stat_label': 'day streak',
                'review_url': f'{base_url}/review/',
            }

        elif email_type == 'verification':
            return {
                'verification_url': f'{base_url}/verify/test-token-12345/',
                'hours_valid': 24,
            }

        return {}

    def _get_template_info(self, email_type):
        """Return (template_name, subject) for each email type."""
        templates = {
            'study_reminder': ('emails/study_reminder', 'Time to study! You have cards waiting'),
            'streak_reminder': ('emails/streak_reminder', "Don't lose your streak!"),
            'weekly_stats': ('emails/weekly_stats', 'Your Weekly Learning Report'),
            'inactivity_nudge': ('emails/inactivity_nudge', 'We miss you!'),
            'achievement': ('emails/achievement', 'Achievement Unlocked: 7-Day Streak'),
            'verification': ('emails/verification', 'Verify your email address'),
        }
        return templates.get(email_type, ('emails/study_reminder', 'Test Email'))
