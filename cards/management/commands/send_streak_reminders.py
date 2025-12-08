"""
Management command to send streak reminder emails.

Run this command hourly (afternoon hours recommended):
    python manage.py send_streak_reminders

Sends reminders to users who:
- Have an active streak (> 0)
- Haven't studied today
- Haven't received a streak reminder today
"""

import zoneinfo
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from cards.models import UserPreferences, Card, EmailLog
from cards.email import send_branded_email, can_send_email


class Command(BaseCommand):
    help = 'Send streak reminder emails to users at risk of losing their streak'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be sent without actually sending emails',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        reminders_sent = 0

        # Find users with active streaks
        users_at_risk = UserPreferences.objects.filter(
            current_streak__gt=0,
        ).select_related('user')

        for prefs in users_at_risk:
            user = prefs.user

            # Check if user has studied today (using their local timezone)
            user_today = prefs.get_local_date()
            if prefs.last_study_date == user_today:
                # Already studied today, no reminder needed
                continue

            # Check if user has email and is active
            if not user.email or not user.is_active:
                continue

            # Check user email preferences
            if not can_send_email(user, 'streak_reminders'):
                self.stdout.write(f"Skipping {user.username}: email preferences disabled")
                continue

            # Check if already sent today
            if EmailLog.was_sent_today(user, EmailLog.EmailType.STREAK_REMINDER):
                self.stdout.write(f"Skipping {user.username}: already sent today")
                continue

            if dry_run:
                self.stdout.write(
                    f"[DRY RUN] Would send to {user.email}: {prefs.current_streak}-day streak at risk"
                )
            else:
                self._send_streak_reminder(user, prefs)
                reminders_sent += 1

        self.stdout.write(
            self.style.SUCCESS(f"Sent {reminders_sent} streak reminder(s)")
        )

    def _send_streak_reminder(self, user, prefs):
        """Send the streak reminder email."""
        subject = f"Don't lose your {prefs.current_streak}-day streak!"

        # Calculate hours remaining until midnight in user's timezone
        user_tz = zoneinfo.ZoneInfo(prefs.user_timezone)
        now_local = timezone.now().astimezone(user_tz)
        # End of day in user's timezone
        local_midnight = now_local.replace(hour=23, minute=59, second=59)
        hours_remaining = max(1, int((local_midnight - now_local).seconds / 3600))

        # Build review URL
        base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000').rstrip('/')
        review_url = f'{base_url}/review/'

        context = {
            'current_streak': prefs.current_streak,
            'hours_remaining': hours_remaining,
            'review_url': review_url,
        }

        send_branded_email(
            user=user,
            subject=subject,
            template_name='emails/streak_reminder',
            context=context,
            fail_silently=False,
        )

        # Log the email
        EmailLog.objects.create(
            user=user,
            email_type=EmailLog.EmailType.STREAK_REMINDER,
            subject=subject,
        )

        self.stdout.write(f"Sent streak reminder to {user.email}: {prefs.current_streak}-day streak")
