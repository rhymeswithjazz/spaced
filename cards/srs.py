"""
Spaced Repetition System (SRS) algorithm implementation.

This module implements the SM-2 algorithm, originally developed by Piotr Wozniak
for SuperMemo. It's a proven algorithm for optimizing review intervals.

The algorithm adjusts the ease factor and interval based on the quality of recall,
with the goal of scheduling reviews just before the memory would fade.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Tuple


# Quality rating constants
QUALITY_BLACKOUT = 0       # Complete blackout, no recognition
QUALITY_WRONG_EASY = 1     # Wrong, but answer seemed easy once seen
QUALITY_WRONG_HARD = 2     # Wrong, but remembered upon seeing answer
QUALITY_HARD = 3           # Correct, but with significant difficulty
QUALITY_GOOD = 4           # Correct, with some hesitation
QUALITY_EASY = 5           # Perfect response, immediate recall

# Algorithm constants
MIN_EASE_FACTOR = 1.3      # Minimum ease factor to prevent cards becoming too hard
DEFAULT_EASE_FACTOR = 2.5  # Starting ease factor for new cards
FIRST_INTERVAL = 1         # First successful review: 1 day
SECOND_INTERVAL = 6        # Second successful review: 6 days


@dataclass(frozen=True)
class ReviewResult:
    """Immutable result of a review calculation."""
    ease_factor: float
    interval: int  # days
    repetitions: int
    next_review: datetime


def calculate_ease_factor(current_ease: float, quality: int) -> float:
    """
    Calculate new ease factor based on review quality.

    The formula adjusts ease factor based on how difficult the recall was:
    EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))

    Where q is the quality rating (0-5).
    """
    adjustment = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ease = current_ease + adjustment
    return max(MIN_EASE_FACTOR, new_ease)


def calculate_interval(
    current_interval: int,
    repetitions: int,
    ease_factor: float,
    quality: int
) -> Tuple[int, int]:
    """
    Calculate the next interval and updated repetition count.

    Returns tuple of (new_interval, new_repetitions).

    For successful reviews (quality >= 3):
    - First review: interval = 1 day
    - Second review: interval = 6 days
    - Subsequent: interval = previous_interval * ease_factor

    For failed reviews (quality < 3):
    - Reset to learning phase with 1-day interval
    """
    if quality < 3:
        # Failed review - reset to learning phase
        return (1, 0)

    # Successful review
    new_repetitions = repetitions + 1

    if repetitions == 0:
        new_interval = FIRST_INTERVAL
    elif repetitions == 1:
        new_interval = SECOND_INTERVAL
    else:
        new_interval = round(current_interval * ease_factor)

    return (new_interval, new_repetitions)


def calculate_review(
    current_ease: float,
    current_interval: int,
    repetitions: int,
    quality: int,
    review_time: datetime | None = None
) -> ReviewResult:
    """
    Calculate the complete review result for a card.

    This is the main entry point for the SM-2 algorithm. It takes the current
    card state and quality rating, returning the new scheduling parameters.

    Args:
        current_ease: Current ease factor of the card
        current_interval: Current interval in days
        repetitions: Number of successful reviews in a row
        quality: Quality of recall (0-5)
        review_time: Time of review (defaults to now)

    Returns:
        ReviewResult with new scheduling parameters
    """
    if quality < 0 or quality > 5:
        raise ValueError(f"Quality must be between 0 and 5, got {quality}")

    if review_time is None:
        review_time = datetime.now()

    new_interval, new_repetitions = calculate_interval(
        current_interval, repetitions, current_ease, quality
    )
    new_ease = calculate_ease_factor(current_ease, quality)
    next_review = review_time + timedelta(days=new_interval)

    return ReviewResult(
        ease_factor=new_ease,
        interval=new_interval,
        repetitions=new_repetitions,
        next_review=next_review
    )


def get_cards_due(cards, now: datetime | None = None):
    """
    Filter cards that are due for review.

    Args:
        cards: Iterable of card objects with next_review attribute
        now: Current time (defaults to now)

    Returns:
        List of cards due for review, sorted by next_review (oldest first)
    """
    if now is None:
        now = datetime.now()

    due_cards = [card for card in cards if card.next_review <= now]
    return sorted(due_cards, key=lambda c: c.next_review)


def estimate_retention(interval: int, ease_factor: float) -> float:
    """
    Estimate memory retention probability at the scheduled review time.

    Uses a simplified forgetting curve model. At the optimal review time,
    retention should be around 90% for well-calibrated intervals.

    This is an approximation for informational purposes.
    """
    # Simplified model: retention decreases exponentially
    # Assumes 90% retention at scheduled review time for perfectly calibrated cards
    base_retention = 0.9

    # Adjust based on ease factor - easier cards (higher EF) retain better
    ease_adjustment = (ease_factor - MIN_EASE_FACTOR) / (DEFAULT_EASE_FACTOR - MIN_EASE_FACTOR)
    ease_boost = 0.05 * ease_adjustment

    return min(0.99, base_retention + ease_boost)
