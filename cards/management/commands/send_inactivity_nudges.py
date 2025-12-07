"""
Management command to send inactivity nudge emails.

Run this command daily:
    python manage.py send_inactivity_nudges

Sends re-engagement emails to users who haven't studied in 3+ days.
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from cards.models import UserPreferences, Card, EmailLog
from cards.email import send_branded_email, can_send_email


# Number of days of inactivity before sending a nudge
INACTIVITY_THRESHOLD_DAYS = 3


class Command(BaseCommand):
    help = 'Send inactivity nudge emails to users who haven\'t studied recently'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be sent without actually sending emails',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=INACTIVITY_THRESHOLD_DAYS,
            help=f'Days of inactivity before sending nudge (default: {INACTIVITY_THRESHOLD_DAYS})',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        threshold_days = options['days']
        now = timezone.now()
        threshold_date = (now - timedelta(days=threshold_days)).date()
        emails_sent = 0

        # Find users who:
        # 1. Have studied before (last_study_date is not null)
        # 2. Haven't studied in threshold_days days
        inactive_users = UserPreferences.objects.filter(
            last_study_date__isnull=False,
            last_study_date__lt=threshold_date,
        ).select_related('user')

        for prefs in inactive_users:
            user = prefs.user

            # Check if user has email and is active
            if not user.email or not user.is_active:
                continue

            # Check user email preferences
            if not can_send_email(user, 'inactivity_nudge'):
                self.stdout.write(f"Skipping {user.username}: email preferences disabled")
                continue

            # Check if already sent a nudge in the last 7 days
            # (don't spam inactive users)
            week_ago = now - timedelta(days=7)
            recent_nudge = EmailLog.objects.filter(
                user=user,
                email_type=EmailLog.EmailType.INACTIVITY_NUDGE,
                sent_at__gte=week_ago
            ).exists()

            if recent_nudge:
                self.stdout.write(f"Skipping {user.username}: nudge sent recently")
                continue

            # Calculate days inactive
            days_inactive = (now.date() - prefs.last_study_date).days

            # Get cards due (excludes new cards that have never been reviewed)
            cards_due = Card.objects.filter(
                deck__owner=user,
                next_review__lte=now,
                has_been_reviewed=True
            ).count()

            if dry_run:
                self.stdout.write(
                    f"[DRY RUN] Would send to {user.email}: "
                    f"{days_inactive} days inactive, {cards_due} cards due"
                )
            else:
                self._send_inactivity_nudge(user, days_inactive, cards_due)
                emails_sent += 1

        self.stdout.write(
            self.style.SUCCESS(f"Sent {emails_sent} inactivity nudge(s)")
        )

    def _send_inactivity_nudge(self, user, days_inactive, cards_due):
        """Send the inactivity nudge email."""
        subject = f"We miss you, {user.username}!"

        # Build review URL
        base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000').rstrip('/')
        review_url = f'{base_url}/review/'

        context = {
            'days_inactive': days_inactive,
            'cards_due': cards_due,
            'review_url': review_url,
        }

        send_branded_email(
            user=user,
            subject=subject,
            template_name='emails/inactivity_nudge',
            context=context,
            fail_silently=False,
        )

        # Log the email
        EmailLog.objects.create(
            user=user,
            email_type=EmailLog.EmailType.INACTIVITY_NUDGE,
            subject=subject,
        )

        self.stdout.write(f"Sent inactivity nudge to {user.email}: {days_inactive} days inactive")
