"""
Management command to send review reminder emails.

Run this command via cron or a scheduled task:
    python manage.py send_reminders

For Docker deployment, add to crontab or use a scheduler container.
"""

from datetime import datetime

from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User

from cards.models import ReviewReminder, Card


class Command(BaseCommand):
    help = 'Send review reminder emails to users with cards due'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be sent without actually sending emails',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()
        current_day = now.weekday()  # 0 = Monday

        reminders_sent = 0

        for reminder in ReviewReminder.objects.filter(enabled=True).select_related('user'):
            if not self._should_send_today(reminder, current_day, now):
                continue

            user = reminder.user
            due_count = self._get_due_cards_count(user)

            if due_count == 0:
                self.stdout.write(f"Skipping {user.username}: no cards due")
                continue

            if dry_run:
                self.stdout.write(
                    f"[DRY RUN] Would send to {user.email}: {due_count} cards due"
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

    def _get_due_cards_count(self, user):
        """Count cards due for review for a user."""
        return Card.objects.filter(
            deck__owner=user,
            next_review__lte=timezone.now()
        ).count()

    def _send_reminder_email(self, user, due_count):
        """Send the reminder email."""
        subject = f"You have {due_count} flashcard{'s' if due_count != 1 else ''} to review"
        message = f"""Hi {user.username},

You have {due_count} flashcard{'s' if due_count != 1 else ''} due for review.

Consistent review is key to effective learning. Take a few minutes to review your cards today!

Happy studying!
"""

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        self.stdout.write(f"Sent reminder to {user.email}: {due_count} cards due")
