"""
Management command to send review reminder emails.

Run this command via cron or a scheduled task (recommended: every 15 minutes):
    python manage.py send_reminders

For Docker deployment, this is automatically scheduled via supercronic.

The command respects each user's preferred_time setting and will only send
reminders within a configurable time window (default: 30 minutes) of that time.
"""

import logging
import traceback

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from cards.models import ReviewReminder, Card, EmailLog, CommandExecutionLog
from cards.email import send_branded_email, can_send_email

logger = logging.getLogger(__name__)

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
        parser.add_argument(
            '--status',
            action='store_true',
            help='Show status of last command execution and exit',
        )

    def handle(self, *args, **options):
        if options['status']:
            return self._show_status()

        dry_run = options['dry_run']
        time_window = options['time_window']
        now = timezone.now()
        local_now = timezone.localtime(now)
        current_day = local_now.weekday()  # 0 = Monday (use local time for day check)

        # Start execution log
        execution_log = None
        if not dry_run:
            execution_log = CommandExecutionLog.start('send_reminders')

        logger.info(
            "Starting send_reminders command",
            extra={
                'dry_run': dry_run,
                'time_window': time_window,
                'server_time': now.isoformat(),
                'server_timezone': str(settings.TIME_ZONE),
            }
        )

        reminders_sent = 0
        users_processed = 0
        errors = []
        skipped_reasons = {
            'not_send_day': 0,
            'outside_time_window': 0,
            'email_prefs_disabled': 0,
            'already_sent_today': 0,
            'no_cards_due': 0,
        }

        try:
            enabled_reminders = ReviewReminder.objects.filter(enabled=True).select_related('user')
            total_enabled = enabled_reminders.count()
            logger.info(f"Found {total_enabled} enabled reminders to process")

            for reminder in enabled_reminders:
                user = reminder.user
                users_processed += 1

                # Check if should send today
                if not self._should_send_today(reminder, current_day, now):
                    logger.info(
                        f"Skipping {user.username}: not a send day "
                        f"(frequency={reminder.frequency}, custom_days={reminder.custom_days}, today=weekday {current_day})"
                    )
                    skipped_reasons['not_send_day'] += 1
                    continue

                # Check if current time is within the preferred time window
                if not self._is_within_preferred_time(reminder, now, time_window):
                    logger.info(
                        f"Skipping {user.username}: outside time window "
                        f"(preferred={reminder.preferred_time}, current={now.time()}, window=±{time_window}min)"
                    )
                    skipped_reasons['outside_time_window'] += 1
                    continue

                # Check user email preferences
                if not can_send_email(user, 'study_reminders'):
                    logger.info(f"Skipping {user.username}: email preferences disabled")
                    self.stdout.write(f"Skipping {user.username}: email preferences disabled")
                    skipped_reasons['email_prefs_disabled'] += 1
                    continue

                # Check if already sent today
                if EmailLog.was_sent_today(user, EmailLog.EmailType.STUDY_REMINDER):
                    logger.info(f"Skipping {user.username}: already sent today")
                    self.stdout.write(f"Skipping {user.username}: already sent today")
                    skipped_reasons['already_sent_today'] += 1
                    continue

                due_count = self._get_due_cards_count(user)

                if due_count == 0:
                    logger.info(f"Skipping {user.username}: no cards due")
                    self.stdout.write(f"Skipping {user.username}: no cards due")
                    skipped_reasons['no_cards_due'] += 1
                    continue

                # User is eligible for reminder
                if dry_run:
                    self.stdout.write(
                        f"[DRY RUN] Would send to {user.email}: {due_count} cards due "
                        f"(preferred time: {reminder.preferred_time})"
                    )
                    logger.info(
                        f"[DRY RUN] Would send to {user.username}",
                        extra={'email': user.email, 'due_count': due_count}
                    )
                else:
                    try:
                        self._send_reminder_email(user, due_count)
                        reminder.last_sent = now
                        reminder.save()
                        reminders_sent += 1
                        logger.info(
                            f"Sent reminder to {user.username}",
                            extra={
                                'email': user.email,
                                'due_count': due_count,
                                'preferred_time': str(reminder.preferred_time),
                            }
                        )
                        self.stdout.write(f"Sent reminder to {user.email}: {due_count} cards due")
                    except Exception as e:
                        error_msg = f"Failed to send email to {user.username}: {str(e)}"
                        errors.append({
                            'user': user.username,
                            'email': user.email,
                            'error': str(e),
                            'traceback': traceback.format_exc(),
                        })
                        logger.error(
                            error_msg,
                            extra={'traceback': traceback.format_exc()},
                            exc_info=True
                        )
                        self.stderr.write(self.style.ERROR(error_msg))

            # Log completion
            summary = {
                'reminders_sent': reminders_sent,
                'users_processed': users_processed,
                'errors_count': len(errors),
                'skipped': skipped_reasons,
            }
            logger.info(
                f"Completed send_reminders: sent {reminders_sent} reminder(s)",
                extra=summary
            )

            if execution_log:
                if errors:
                    execution_log.finish_failure(
                        error_message=f"{len(errors)} email(s) failed to send",
                        errors_count=len(errors),
                        details={**summary, 'errors': errors}
                    )
                else:
                    execution_log.finish_success(
                        users_processed=users_processed,
                        emails_sent=reminders_sent,
                        details=summary
                    )

            self.stdout.write(
                self.style.SUCCESS(f"Sent {reminders_sent} reminder(s)")
            )

        except Exception as e:
            error_msg = f"Command failed with error: {str(e)}"
            logger.critical(error_msg, exc_info=True)
            if execution_log:
                execution_log.finish_failure(
                    error_message=error_msg,
                    details={'traceback': traceback.format_exc()}
                )
            raise

    def _show_status(self):
        """Show status of last command execution."""
        last_run = CommandExecutionLog.get_last_run('send_reminders')
        last_success = CommandExecutionLog.get_last_success('send_reminders')

        self.stdout.write("\n=== send_reminders Status ===\n")

        if last_run:
            self.stdout.write(f"Last run: {last_run.started_at}")
            self.stdout.write(f"  Status: {last_run.status}")
            self.stdout.write(f"  Users processed: {last_run.users_processed}")
            self.stdout.write(f"  Emails sent: {last_run.emails_sent}")
            if last_run.error_message:
                self.stdout.write(f"  Error: {last_run.error_message}")
        else:
            self.stdout.write("No execution history found.")

        if last_success and last_success != last_run:
            self.stdout.write(f"\nLast successful run: {last_success.started_at}")
            self.stdout.write(f"  Emails sent: {last_success.emails_sent}")

        # Show enabled reminders count
        enabled_count = ReviewReminder.objects.filter(enabled=True).count()
        self.stdout.write(f"\nEnabled reminders: {enabled_count}")

        # Show server time info
        now = timezone.now()
        self.stdout.write(f"\nServer time: {now}")
        self.stdout.write(f"Server timezone: {settings.TIME_ZONE}")

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
        # Convert to local time (respects Django TIME_ZONE setting)
        # This is important because preferred_time is stored in the user's local timezone
        local_now = timezone.localtime(now)
        current_time = local_now.time()
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
        """Count cards due for review for a user (excludes new cards)."""
        return Card.objects.filter(
            deck__owner=user,
            next_review__lte=timezone.now(),
            repetitions__gt=0  # Exclude new cards (never reviewed)
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
