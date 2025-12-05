import secrets

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from . import srs


class Deck(models.Model):
    """A collection of flashcards."""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='decks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ['name', 'owner']

    def __str__(self):
        return self.name

    def cards_due_count(self):
        """Return count of cards due for review."""
        return self.cards.filter(next_review__lte=timezone.now()).count()


class Card(models.Model):
    """A flashcard with spaced repetition tracking."""

    class CardType(models.TextChoices):
        BASIC = 'basic', 'Basic (Front/Back)'
        CLOZE = 'cloze', 'Cloze Deletion'
        REVERSE = 'reverse', 'Basic + Reverse'

    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name='cards')
    card_type = models.CharField(
        max_length=20,
        choices=CardType.choices,
        default=CardType.BASIC
    )
    front = models.TextField(help_text="Question or prompt (use {{c1::text}} for cloze)")
    back = models.TextField(help_text="Answer", blank=True)
    notes = models.TextField(blank=True, help_text="Additional notes or hints")

    # Spaced repetition fields (SM-2 algorithm inspired)
    ease_factor = models.FloatField(default=2.5)  # Difficulty multiplier
    interval = models.IntegerField(default=0)  # Days until next review
    repetitions = models.IntegerField(default=0)  # Successful reviews in a row
    next_review = models.DateTimeField(default=timezone.now)
    last_reviewed = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['next_review']

    def __str__(self):
        return f"{self.front[:50]}..."

    def is_due(self):
        """Check if card is due for review."""
        return self.next_review <= timezone.now()

    def review(self, quality):
        """
        Update card scheduling based on review quality using SM-2 algorithm.

        Quality ratings (0-5):
        0 - Complete blackout
        1 - Incorrect, but recognized answer
        2 - Incorrect, but easy to recall
        3 - Correct with serious difficulty
        4 - Correct with some hesitation
        5 - Perfect response

        Returns the ReviewLog entry created.
        """
        # Store current state for logging
        ease_before = self.ease_factor
        interval_before = self.interval

        # Calculate new scheduling using SRS algorithm
        result = srs.calculate_review(
            current_ease=self.ease_factor,
            current_interval=self.interval,
            repetitions=self.repetitions,
            quality=quality,
            review_time=timezone.now()
        )

        # Update card state
        self.ease_factor = result.ease_factor
        self.interval = result.interval
        self.repetitions = result.repetitions
        self.next_review = result.next_review
        self.last_reviewed = timezone.now()
        self.save()

        # Create review log
        return ReviewLog.objects.create(
            card=self,
            quality=quality,
            ease_factor_before=ease_before,
            ease_factor_after=result.ease_factor,
            interval_before=interval_before,
            interval_after=result.interval
        )


class ReviewLog(models.Model):
    """Log of card reviews for analytics."""
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='review_logs')
    quality = models.IntegerField()
    ease_factor_before = models.FloatField()
    ease_factor_after = models.FloatField()
    interval_before = models.IntegerField()
    interval_after = models.IntegerField()
    reviewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-reviewed_at']


class ReviewReminder(models.Model):
    """Email reminder settings for a user."""

    class Frequency(models.TextChoices):
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'
        CUSTOM = 'custom', 'Custom Days'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='reminder')
    enabled = models.BooleanField(default=True)
    frequency = models.CharField(
        max_length=20,
        choices=Frequency.choices,
        default=Frequency.DAILY
    )
    preferred_time = models.TimeField(default='09:00')
    # For custom frequency - comma-separated days (0=Monday, 6=Sunday)
    custom_days = models.CharField(max_length=20, blank=True, default='0,1,2,3,4')
    last_sent = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Reminder for {self.user.username}"


class UserPreferences(models.Model):
    """User preferences including theme settings."""

    class Theme(models.TextChoices):
        LIGHT = 'light', 'Light'
        DARK = 'dark', 'Dark'
        SYSTEM = 'system', 'System'

    class TextSize(models.TextChoices):
        SMALL = 'small', 'Small'
        MEDIUM = 'medium', 'Medium'
        LARGE = 'large', 'Large'
        XLARGE = 'xlarge', 'Extra Large'
        XXLARGE = 'xxlarge', '2X Large'
        XXXLARGE = 'xxxlarge', '3X Large'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    theme = models.CharField(
        max_length=10,
        choices=Theme.choices,
        default=Theme.SYSTEM
    )
    card_text_size = models.CharField(
        max_length=10,
        choices=TextSize.choices,
        default=TextSize.LARGE
    )
    cards_per_session = models.IntegerField(default=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'User preferences'

    def __str__(self):
        return f"Preferences for {self.user.username}"


class EmailVerificationToken(models.Model):
    """Token for verifying user email addresses."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_verification')
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Verification token for {self.user.username}"

    @classmethod
    def create_for_user(cls, user):
        """Create a new verification token for a user, replacing any existing one."""
        cls.objects.filter(user=user).delete()
        token = secrets.token_urlsafe(32)
        return cls.objects.create(user=user, token=token)

    def is_expired(self):
        """Check if the token has expired (24 hours)."""
        from datetime import timedelta
        return timezone.now() > self.created_at + timedelta(hours=24)
