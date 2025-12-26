"""Review session views."""

import json
import random

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..models import Deck, Card
from .. import cloze
from ..achievements import check_and_send_achievements
from .helpers import get_or_create_preferences


@login_required
def review_session(request, deck_pk=None):
    """Start a review session."""
    user = request.user
    preferences = get_or_create_preferences(user)
    now = timezone.now()

    # Get deck filter if specified
    if deck_pk:
        deck = get_object_or_404(Deck, pk=deck_pk, owner=user)
        deck_filter = {'deck': deck}
    else:
        deck = None
        deck_filter = {'deck__owner': user}

    # Anki-like behavior: prioritize ALL due cards, then add limited new cards
    # Due cards: reviewed before, scheduled for now or earlier
    due_cards_query = Card.objects.filter(
        **deck_filter,
        next_review__lte=now,
        has_been_reviewed=True
    ).select_related('deck')

    # Apply max reviews limit if set (0 = unlimited)
    if preferences.max_reviews_per_session > 0:
        due_cards = list(due_cards_query[:preferences.max_reviews_per_session])
    else:
        due_cards = list(due_cards_query)

    # Add new cards up to the daily limit
    new_cards = list(Card.objects.filter(
        **deck_filter,
        has_been_reviewed=False
    ).select_related('deck')[:preferences.new_cards_per_day])

    cards = due_cards + new_cards

    if not cards:
        messages.info(request, 'No cards due for review!' if not deck else f'No cards due in "{deck.name}"!')
        return redirect('dashboard')

    # Serialize cards for JavaScript
    # For cloze cards, expand into multiple items (one per cloze number)
    cards_data = []
    for card in cards:
        if card.card_type == Card.CardType.CLOZE:
            # Get unique cloze numbers and create an item for each
            cloze_numbers = cloze.get_cloze_numbers(card.front)
            for num in sorted(cloze_numbers):
                cards_data.append({
                    'id': card.pk,
                    'front': card.front,
                    'back': card.back,
                    'notes': card.notes,
                    'card_type': card.card_type,
                    'active_cloze': num,
                })
        else:
            cards_data.append({
                'id': card.pk,
                'front': card.front,
                'back': card.back,
                'notes': card.notes,
                'card_type': card.card_type,
                'active_cloze': None,
            })

    # Shuffle cards for variety
    random.shuffle(cards_data)

    cards_json = json.dumps(cards_data)

    context = {
        'cards': cards,
        'cards_json': cards_json,
        'deck': deck,
        'total_due': len(cards_data),  # Use expanded count for cloze cards
        'text_size': preferences.card_text_size,
        'celebration_animations': preferences.celebration_animations,
    }
    return render(request, 'cards/review_session.html', context)


@login_required
def review_struggling(request):
    """Start a review session for struggling cards (low ease factor)."""
    user = request.user
    preferences = get_or_create_preferences(user)
    target_session_size = 20

    # Struggling cards: low ease factor and have been reviewed at least once
    struggling_cards = list(Card.objects.filter(
        deck__owner=user,
        ease_factor__lt=2.0,
        has_been_reviewed=True
    ).select_related('deck'))

    if not struggling_cards:
        messages.info(request, 'No struggling cards to review!')
        return redirect('dashboard')

    # Serialize cards for JavaScript
    # For cloze cards, expand into multiple items (one per cloze number)
    cards_data = []
    for card in struggling_cards:
        if card.card_type == Card.CardType.CLOZE:
            # Get unique cloze numbers and create an item for each
            cloze_numbers = cloze.get_cloze_numbers(card.front)
            for num in sorted(cloze_numbers):
                cards_data.append({
                    'id': card.pk,
                    'front': card.front,
                    'back': card.back,
                    'notes': card.notes,
                    'card_type': card.card_type,
                    'active_cloze': num,
                })
        else:
            cards_data.append({
                'id': card.pk,
                'front': card.front,
                'back': card.back,
                'notes': card.notes,
                'card_type': card.card_type,
                'active_cloze': None,
            })

    # Shuffle first, then adjust to target session size
    random.shuffle(cards_data)

    # If more than target, trim to target size
    # If fewer than target, repeat cards to fill the session
    if len(cards_data) > target_session_size:
        cards_data = cards_data[:target_session_size]
    elif len(cards_data) < target_session_size:
        # Repeat cards cyclically until we reach target size
        original_cards = cards_data.copy()
        while len(cards_data) < target_session_size:
            cards_data.append(original_cards[len(cards_data) % len(original_cards)])
        # Shuffle again so repeated cards aren't in predictable order
        random.shuffle(cards_data)

    cards_json = json.dumps(cards_data)

    context = {
        'cards': struggling_cards,
        'cards_json': cards_json,
        'deck': None,
        'total_due': len(cards_data),
        'text_size': preferences.card_text_size,
        'celebration_animations': preferences.celebration_animations,
        'session_type': 'struggling',
    }
    return render(request, 'cards/review_session.html', context)


@login_required
@require_POST
def review_card(request, pk):
    """Submit a review for a card."""
    card = get_object_or_404(Card, pk=pk, deck__owner=request.user)

    try:
        data = json.loads(request.body)
        quality = int(data.get('quality', 0))
    except (json.JSONDecodeError, ValueError, TypeError):
        return JsonResponse({'error': 'Invalid request'}, status=400)

    if quality < 0 or quality > 5:
        return JsonResponse({'error': 'Quality must be 0-5'}, status=400)

    card.review(quality)

    # Update user's streak
    prefs = get_or_create_preferences(request.user)
    prefs.update_streak()

    # Check for achievements (sends emails asynchronously-safe)
    awarded_achievements = check_and_send_achievements(request.user)

    return JsonResponse({
        'success': True,
        'next_review': card.next_review.isoformat(),
        'interval': card.interval,
        'ease_factor': round(card.ease_factor, 2),
        'achievements': awarded_achievements,
    })


@login_required
def practice_session(request, deck_pk=None):
    """Start a practice session for cards not yet due.
    
    Practice mode allows users to review cards before they're scheduled,
    without affecting the SRS algorithm. This helps maintain streaks when
    no cards are due.
    """
    user = request.user
    preferences = get_or_create_preferences(user)
    now = timezone.now()
    target_session_size = 20

    # Get deck filter if specified
    if deck_pk:
        deck = get_object_or_404(Deck, pk=deck_pk, owner=user)
        deck_filter = {'deck': deck}
    else:
        deck = None
        deck_filter = {'deck__owner': user}

    # Practice cards: reviewed before, NOT yet due, ordered by soonest
    practice_cards = list(Card.objects.filter(
        **deck_filter,
        next_review__gt=now,
        has_been_reviewed=True
    ).select_related('deck').order_by('next_review')[:target_session_size])

    if not practice_cards:
        messages.info(
            request, 
            'No cards available for practice!' if not deck 
            else f'No cards available for practice in "{deck.name}"!'
        )
        return redirect('dashboard')

    # Serialize cards for JavaScript (same format as review_session)
    cards_data = []
    for card in practice_cards:
        if card.card_type == Card.CardType.CLOZE:
            cloze_numbers = cloze.get_cloze_numbers(card.front)
            for num in sorted(cloze_numbers):
                cards_data.append({
                    'id': card.pk,
                    'front': card.front,
                    'back': card.back,
                    'notes': card.notes,
                    'card_type': card.card_type,
                    'active_cloze': num,
                })
        else:
            cards_data.append({
                'id': card.pk,
                'front': card.front,
                'back': card.back,
                'notes': card.notes,
                'card_type': card.card_type,
                'active_cloze': None,
            })

    # Shuffle for variety
    random.shuffle(cards_data)

    cards_json = json.dumps(cards_data)

    context = {
        'cards': practice_cards,
        'cards_json': cards_json,
        'deck': deck,
        'total_due': len(cards_data),
        'text_size': preferences.card_text_size,
        'celebration_animations': preferences.celebration_animations,
        'practice_mode': True,  # Flag for template to show practice UI
    }
    return render(request, 'cards/review_session.html', context)


@login_required
@require_POST
def practice_card(request, pk):
    """Submit a practice review for a card.
    
    Unlike regular reviews, practice reviews:
    - Do NOT update the card's SRS scheduling
    - Do NOT create ReviewLog entries
    - DO update the user's streak (main purpose of practice mode)
    """
    card = get_object_or_404(Card, pk=pk, deck__owner=request.user)

    try:
        data = json.loads(request.body)
        quality = int(data.get('quality', 0))
    except (json.JSONDecodeError, ValueError, TypeError):
        return JsonResponse({'error': 'Invalid request'}, status=400)

    if quality < 0 or quality > 5:
        return JsonResponse({'error': 'Quality must be 0-5'}, status=400)

    # Update user's streak (the main purpose of practice mode)
    prefs = get_or_create_preferences(request.user)
    prefs.update_streak()

    # Return success but no scheduling info (card wasn't actually updated)
    return JsonResponse({
        'success': True,
        'practice_mode': True,
        'correct': quality >= 3,  # For UI feedback
    })
