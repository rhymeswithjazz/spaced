"""Dashboard view."""

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.shortcuts import render
from django.utils import timezone

from ..models import Deck, Card, ReviewLog


@login_required
def dashboard(request):
    """Main dashboard showing overview and due cards."""
    user = request.user
    now = timezone.now()
    today = now.date()

    # Base querysets
    user_cards = Card.objects.filter(deck__owner=user)
    user_reviews = ReviewLog.objects.filter(card__deck__owner=user)

    # Get deck statistics
    decks = Deck.objects.filter(owner=user).annotate(
        card_count=Count('cards'),
        due_count=Count('cards', filter=Q(cards__next_review__lte=now))
    )

    total_cards = user_cards.count()
    total_due = user_cards.filter(next_review__lte=now).count()

    # === PROGRESS STATS ===
    # Card status: New (never reviewed), Learning (interval < 21), Mature (interval >= 21)
    cards_new = user_cards.filter(repetitions=0).count()
    cards_learning = user_cards.filter(repetitions__gt=0, interval__lt=21).count()
    cards_mature = user_cards.filter(interval__gte=21).count()

    # Retention rate (% of reviews answered correctly - quality >= 3)
    total_reviews_ever = user_reviews.count()
    correct_reviews = user_reviews.filter(quality__gte=3).count()
    retention_rate = round((correct_reviews / total_reviews_ever * 100) if total_reviews_ever > 0 else 0, 1)

    # Average ease factor
    avg_ease = user_cards.aggregate(avg=Avg('ease_factor'))['avg'] or 2.5

    # Struggling cards (ease factor < 2.0 and has been reviewed)
    struggling_cards = user_cards.filter(ease_factor__lt=2.0, repetitions__gt=0).count()

    # === ACTIVITY STATS ===
    # Reviews today/this week/this month
    reviews_today = user_reviews.filter(reviewed_at__date=today).count()

    week_start = today - timezone.timedelta(days=today.weekday())
    reviews_this_week = user_reviews.filter(reviewed_at__date__gte=week_start).count()

    month_start = today.replace(day=1)
    reviews_this_month = user_reviews.filter(reviewed_at__date__gte=month_start).count()

    # Average reviews per day (last 30 days)
    thirty_days_ago = today - timezone.timedelta(days=30)
    reviews_last_30 = user_reviews.filter(reviewed_at__date__gte=thirty_days_ago).count()
    avg_reviews_per_day = round(reviews_last_30 / 30, 1)

    # Study streak (consecutive days with reviews)
    streak = 0
    for i in range(365):
        day = today - timezone.timedelta(days=i)
        if user_reviews.filter(reviewed_at__date=day).exists():
            streak += 1
        else:
            break

    # Longest streak (scan all review dates)
    review_dates = set(
        user_reviews.values_list('reviewed_at__date', flat=True).distinct()
    )
    longest_streak = 0
    if review_dates:
        sorted_dates = sorted(review_dates)
        current_streak = 1
        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i] - sorted_dates[i-1]).days == 1:
                current_streak += 1
            else:
                longest_streak = max(longest_streak, current_streak)
                current_streak = 1
        longest_streak = max(longest_streak, current_streak)

    # === FORECAST STATS ===
    tomorrow = today + timezone.timedelta(days=1)
    due_tomorrow = user_cards.filter(
        next_review__date=tomorrow
    ).count()

    # Due in next 7 days (by day)
    forecast = []
    for i in range(7):
        day = today + timezone.timedelta(days=i)
        if i == 0:
            # Today: cards currently due
            count = total_due
        else:
            count = user_cards.filter(next_review__date=day).count()
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
        deck_new = deck_cards.filter(repetitions=0).count()
        deck_learning = deck_cards.filter(repetitions__gt=0, interval__lt=21).count()
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
        'avg_reviews_per_day': avg_reviews_per_day,
        'longest_streak': longest_streak,
        # Forecast
        'due_tomorrow': due_tomorrow,
        'forecast': forecast,
        # Per-deck
        'deck_stats': deck_stats,
    }
    return render(request, 'cards/dashboard.html', context)
