"""
Management command to send review reminder emails.

Run this command via cron or a scheduled task (recommended: every 15 minutes):
    python manage.py send_reminders

For Docker deployment, add to crontab or use a scheduler container.

The command respects each user's preferred_time setting and will only send
reminders within a configurable time window (default: 30 minutes) of that time.
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User

from cards.models import ReviewReminder, Card, EmailLog
from cards.email import send_branded_email, can_send_email

# Default time window in minutes (send if within this many minutes of preferred time)
DEFAULT_TIME_WINDOW = 30


class Command(BaseCommand):
    help = 'Send review reminder emails to users with cards due'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be sent without actually sending emails',
        )
        parser.add_argument(
            '--time-window',
            type=int,
            default=DEFAULT_TIME_WINDOW,
            help=f'Minutes before/after preferred time to send (default: {DEFAULT_TIME_WINDOW})',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        time_window = options['time_window']
        now = timezone.now()
        current_day = now.weekday()  # 0 = Monday

        reminders_sent = 0

        for reminder in ReviewReminder.objects.filter(enabled=True).select_related('user'):
            if not self._should_send_today(reminder, current_day, now):
                continue

            # Check if current time is within the preferred time window
            if not self._is_within_preferred_time(reminder, now, time_window):
                continue

            user = reminder.user

            # Check user email preferences
            if not can_send_email(user, 'study_reminders'):
                self.stdout.write(f"Skipping {user.username}: email preferences disabled")
                continue

            # Check if already sent today
            if EmailLog.was_sent_today(user, EmailLog.EmailType.STUDY_REMINDER):
                self.stdout.write(f"Skipping {user.username}: already sent today")
                continue

            due_count = self._get_due_cards_count(user)

            if due_count == 0:
                self.stdout.write(f"Skipping {user.username}: no cards due")
                continue

            if dry_run:
                self.stdout.write(
                    f"[DRY RUN] Would send to {user.email}: {due_count} cards due "
                    f"(preferred time: {reminder.preferred_time})"
                )
            else:
                self._send_reminder_email(user, due_count)
                reminder.last_sent = now
                reminder.save()
                reminders_sent += 1

        self.stdout.write(
            self.style.SUCCESS(f"Sent {reminders_sent} reminder(s)")
        )

    def _should_send_today(self, reminder, current_day, now):
        """Check if reminder should be sent today based on frequency settings."""
        if reminder.frequency == ReviewReminder.Frequency.DAILY:
            return True
        elif reminder.frequency == ReviewReminder.Frequency.WEEKLY:
            return current_day == 0  # Monday
        elif reminder.frequency == ReviewReminder.Frequency.CUSTOM:
            allowed_days = [int(d) for d in reminder.custom_days.split(',') if d]
            return current_day in allowed_days
        return False

    def _is_within_preferred_time(self, reminder, now, time_window_minutes):
        """
        Check if the current time is within the time window of the user's preferred time.

        Args:
            reminder: ReviewReminder instance with preferred_time field
            now: Current datetime (timezone-aware)
            time_window_minutes: Number of minutes before/after preferred time to allow

        Returns:
            True if current time is within the window, False otherwise
        """
        # Get current time components
        current_time = now.time()
        preferred = reminder.preferred_time

        # Convert times to minutes since midnight for easier comparison
        current_minutes = current_time.hour * 60 + current_time.minute
        preferred_minutes = preferred.hour * 60 + preferred.minute

        # Calculate the difference, handling midnight wraparound
        diff = abs(current_minutes - preferred_minutes)

        # Handle wraparound (e.g., preferred=23:45, current=00:15 should be 30 min apart)
        if diff > 12 * 60:  # More than 12 hours apart, use the shorter path
            diff = 24 * 60 - diff

        return diff <= time_window_minutes

    def _get_due_cards_count(self, user):
        """Count cards due for review for a user."""
        return Card.objects.filter(
            deck__owner=user,
            next_review__lte=timezone.now()
        ).count()

    def _send_reminder_email(self, user, due_count):
        """Send the reminder email using branded template."""
        subject = f"You have {due_count} flashcard{'s' if due_count != 1 else ''} to review"

        # Get current streak from preferences
        prefs = getattr(user, 'preferences', None)
        current_streak = prefs.current_streak if prefs else 0

        # Build review URL
        base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000').rstrip('/')
        review_url = f'{base_url}/review/'

        context = {
            'due_count': due_count,
            'current_streak': current_streak,
            'review_url': review_url,
        }

        send_branded_email(
            user=user,
            subject=subject,
            template_name='emails/study_reminder',
            context=context,
            fail_silently=False,
        )

        # Log the email
        EmailLog.objects.create(
            user=user,
            email_type=EmailLog.EmailType.STUDY_REMINDER,
            subject=subject,
        )

        self.stdout.write(f"Sent reminder to {user.email}: {due_count} cards due")
