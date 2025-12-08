"""Dashboard view."""

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.shortcuts import render
from django.utils import timezone

from ..models import Deck, Card, ReviewLog
from .helpers import (
    get_or_create_preferences,
    get_user_local_date,
    get_local_day_range,
    get_local_day_start,
)


@login_required
def dashboard(request):
    """Main dashboard showing overview and due cards."""
    user = request.user
    now = timezone.now()
    today = get_user_local_date(user)  # Use user's local date, not UTC

    # Base querysets
    user_cards = Card.objects.filter(deck__owner=user)
    user_reviews = ReviewLog.objects.filter(card__deck__owner=user)

    # Get deck statistics
    decks = Deck.objects.filter(owner=user).annotate(
        card_count=Count('cards'),
        due_count=Count('cards', filter=Q(
            cards__next_review__lte=now,
            cards__has_been_reviewed=True  # Exclude new cards
        )),
        new_count=Count('cards', filter=Q(cards__has_been_reviewed=False))
    )

    total_cards = user_cards.count()
    # Due = cards that have been reviewed before and are scheduled for review
    total_due = user_cards.filter(next_review__lte=now, has_been_reviewed=True).count()
    # New = cards that have never been reviewed
    total_new = user_cards.filter(has_been_reviewed=False).count()

    # === PROGRESS STATS ===
    # Card status: New (never reviewed), Learning (interval < 21), Mature (interval >= 21)
    cards_new = user_cards.filter(has_been_reviewed=False).count()
    cards_learning = user_cards.filter(has_been_reviewed=True, interval__lt=21).count()
    cards_mature = user_cards.filter(interval__gte=21).count()

    # Retention rate (% of reviews answered correctly - quality >= 3)
    total_reviews_ever = user_reviews.count()
    correct_reviews = user_reviews.filter(quality__gte=3).count()
    retention_rate = round((correct_reviews / total_reviews_ever * 100) if total_reviews_ever > 0 else 0, 1)

    # Average ease factor
    avg_ease = user_cards.aggregate(avg=Avg('ease_factor'))['avg'] or 2.5

    # Struggling cards (ease factor < 2.0 and has been reviewed)
    struggling_cards = user_cards.filter(ease_factor__lt=2.0, has_been_reviewed=True).count()

    # === ACTIVITY STATS ===
    # Reviews today/this week/this month (using user's local timezone)
    today_start, today_end = get_local_day_range(user, today)
    reviews_today = user_reviews.filter(
        reviewed_at__gte=today_start,
        reviewed_at__lt=today_end
    ).count()

    week_start = today - timedelta(days=today.weekday())
    week_start_utc = get_local_day_start(user, week_start)
    reviews_this_week = user_reviews.filter(reviewed_at__gte=week_start_utc).count()

    month_start = today.replace(day=1)
    month_start_utc = get_local_day_start(user, month_start)
    reviews_this_month = user_reviews.filter(reviewed_at__gte=month_start_utc).count()

    # Average reviews per day (last 30 days)
    thirty_days_ago = today - timedelta(days=30)
    thirty_days_ago_utc = get_local_day_start(user, thirty_days_ago)
    reviews_last_30 = user_reviews.filter(reviewed_at__gte=thirty_days_ago_utc).count()
    avg_reviews_per_day = round(reviews_last_30 / 30, 1)

    # Study streak - use stored values from UserPreferences
    # These are updated when user completes reviews (see update_streak method)
    preferences = get_or_create_preferences(user)

    # Check if streak is still valid (studied today or yesterday)
    # If user hasn't studied in more than 1 day, streak should be 0
    if preferences.last_study_date is not None:
        days_since_study = (today - preferences.last_study_date).days
        if days_since_study > 1:
            # Streak is broken - reset it
            streak = 0
            if preferences.current_streak != 0:
                preferences.current_streak = 0
                preferences.save(update_fields=['current_streak'])
        else:
            streak = preferences.current_streak
    else:
        streak = 0

    longest_streak = preferences.longest_streak

    # === FORECAST STATS ===
    tomorrow = today + timedelta(days=1)
    tomorrow_start, tomorrow_end = get_local_day_range(user, tomorrow)
    due_tomorrow = user_cards.filter(
        next_review__gte=tomorrow_start,
        next_review__lt=tomorrow_end
    ).count()

    # Due in next 7 days (by day)
    forecast = []
    for i in range(7):
        day = today + timedelta(days=i)
        if i == 0:
            # Today: cards currently due
            count = total_due
        else:
            day_start, day_end = get_local_day_range(user, day)
            count = user_cards.filter(next_review__gte=day_start, next_review__lt=day_end).count()
        forecast.append({
            'day': day,
            'day_name': 'Today' if i == 0 else ('Tomorrow' if i == 1 else day.strftime('%a')),
            'count': count
        })

    # === PER-DECK STATS ===
    deck_stats = []
    for deck in decks:
        deck_reviews = user_reviews.filter(card__deck=deck)
        deck_total_reviews = deck_reviews.count()
        deck_correct = deck_reviews.filter(quality__gte=3).count()
        deck_retention = round((deck_correct / deck_total_reviews * 100) if deck_total_reviews > 0 else 0, 1)

        deck_cards = user_cards.filter(deck=deck)
        deck_new = deck_cards.filter(has_been_reviewed=False).count()
        deck_learning = deck_cards.filter(has_been_reviewed=True, interval__lt=21).count()
        deck_mature = deck_cards.filter(interval__gte=21).count()

        deck_stats.append({
            'deck': deck,
            'retention': deck_retention,
            'total_reviews': deck_total_reviews,
            'new': deck_new,
            'learning': deck_learning,
            'mature': deck_mature,
        })

    context = {
        'decks': decks,
        'total_cards': total_cards,
        'total_due': total_due,
        'total_new': total_new,
        'streak': streak,
        # Progress
        'cards_new': cards_new,
        'cards_learning': cards_learning,
        'cards_mature': cards_mature,
        'retention_rate': retention_rate,
        'avg_ease': round(avg_ease, 2),
        'struggling_cards': struggling_cards,
        # Activity
        'reviews_today': reviews_today,
        'reviews_this_week': reviews_this_week,
        'reviews_this_month': reviews_this_month,
        'total_reviews': total_reviews_ever,
        'avg_reviews_per_day': avg_reviews_per_day,
        'longest_streak': longest_streak,
        # Forecast
        'due_tomorrow': due_tomorrow,
        'forecast': forecast,
        # Per-deck
        'deck_stats': deck_stats,
    }
    return render(request, 'cards/dashboard.html', context)
