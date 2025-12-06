"""
Management command to send weekly statistics emails.

Run this command on Sundays:
    python manage.py send_weekly_stats

Sends weekly progress summary to all active users.
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Avg, Count
from django.utils import timezone

from cards.models import UserPreferences, Card, ReviewLog, Deck, EmailLog
from cards.email import send_branded_email, can_send_email


class Command(BaseCommand):
    help = 'Send weekly statistics emails to users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be sent without actually sending emails',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()
        emails_sent = 0

        # Calculate date ranges
        week_end = now.date()
        week_start = week_end - timedelta(days=7)
        prev_week_end = week_start
        prev_week_start = prev_week_end - timedelta(days=7)

        # Get all users with preferences
        for prefs in UserPreferences.objects.select_related('user').all():
            user = prefs.user

            # Check if user has email and is active
            if not user.email or not user.is_active:
                continue

            # Check user email preferences
            if not can_send_email(user, 'weekly_stats'):
                self.stdout.write(f"Skipping {user.username}: email preferences disabled")
                continue

            # Check if already sent this week
            if EmailLog.was_sent_this_week(user, EmailLog.EmailType.WEEKLY_STATS):
                self.stdout.write(f"Skipping {user.username}: already sent this week")
                continue

            # Gather statistics
            stats = self._gather_stats(user, week_start, week_end, prev_week_start, prev_week_end)

            # Skip if no activity at all
            if stats['cards_reviewed'] == 0 and stats['cards_reviewed_last_week'] == 0:
                self.stdout.write(f"Skipping {user.username}: no activity")
                continue

            if dry_run:
                self.stdout.write(
                    f"[DRY RUN] Would send to {user.email}: "
                    f"{stats['cards_reviewed']} cards reviewed this week"
                )
            else:
                self._send_weekly_stats(user, prefs, stats, week_start, week_end)
                emails_sent += 1

        self.stdout.write(
            self.style.SUCCESS(f"Sent {emails_sent} weekly stats email(s)")
        )

    def _gather_stats(self, user, week_start, week_end, prev_week_start, prev_week_end):
        """Gather weekly statistics for a user."""
        # This week's reviews
        this_week_reviews = ReviewLog.objects.filter(
            card__deck__owner=user,
            reviewed_at__date__gte=week_start,
            reviewed_at__date__lte=week_end,
        )

        # Last week's reviews
        last_week_reviews = ReviewLog.objects.filter(
            card__deck__owner=user,
            reviewed_at__date__gte=prev_week_start,
            reviewed_at__date__lt=prev_week_end,
        )

        # Calculate stats
        cards_reviewed = this_week_reviews.count()
        cards_reviewed_last_week = last_week_reviews.count()

        # Average rating
        avg_rating_data = this_week_reviews.aggregate(avg=Avg('quality'))
        average_rating = avg_rating_data['avg']
        average_rating_percentage = int((average_rating / 5) * 100) if average_rating else 0

        # Cards due
        cards_due = Card.objects.filter(
            deck__owner=user,
            next_review__lte=timezone.now()
        ).count()

        # Per-deck breakdown
        deck_stats = []
        deck_counts = this_week_reviews.values('card__deck__name').annotate(
            count=Count('id')
        ).order_by('-count')[:5]

        for item in deck_counts:
            deck_stats.append({
                'name': item['card__deck__name'],
                'count': item['count'],
            })

        return {
            'cards_reviewed': cards_reviewed,
            'cards_reviewed_last_week': cards_reviewed_last_week,
            'average_rating': average_rating,
            'average_rating_percentage': average_rating_percentage,
            'cards_due': cards_due,
            'deck_stats': deck_stats,
        }

    def _send_weekly_stats(self, user, prefs, stats, week_start, week_end):
        """Send the weekly stats email."""
        subject = f"Your Weekly Progress: {stats['cards_reviewed']} cards reviewed"

        # Build review URL
        base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000').rstrip('/')
        review_url = f'{base_url}/review/'

        context = {
            'week_start': week_start,
            'week_end': week_end,
            'cards_reviewed': stats['cards_reviewed'],
            'cards_reviewed_last_week': stats['cards_reviewed_last_week'],
            'current_streak': prefs.current_streak,
            'average_rating': stats['average_rating'],
            'average_rating_percentage': stats['average_rating_percentage'],
            'cards_due': stats['cards_due'],
            'deck_stats': stats['deck_stats'],
            'review_url': review_url,
        }

        send_branded_email(
            user=user,
            subject=subject,
            template_name='emails/weekly_stats',
            context=context,
            fail_silently=False,
        )

        # Log the email
        EmailLog.objects.create(
            user=user,
            email_type=EmailLog.EmailType.WEEKLY_STATS,
            subject=subject,
        )

        self.stdout.write(f"Sent weekly stats to {user.email}")
