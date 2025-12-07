import secrets
import uuid

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
        """Return count of cards due for review (excludes new cards)."""
        return self.cards.filter(
            next_review__lte=timezone.now(),
            has_been_reviewed=True  # Exclude new cards (never reviewed)
        ).count()

    def cards_new_count(self):
        """Return count of new cards (never reviewed)."""
        return self.cards.filter(has_been_reviewed=False).count()


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
    has_been_reviewed = models.BooleanField(default=False)  # True after first review

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['next_review']

    def __str__(self):
        return f"{self.front[:50]}..."

    def is_due(self):
        """Check if card is due for review (excludes new cards)."""
        return self.repetitions > 0 and self.next_review <= timezone.now()

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
        self.has_been_reviewed = True
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
    """User preferences including theme settings and email notifications."""

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

    # Email notification preferences
    email_study_reminders = models.BooleanField(default=True)
    email_streak_reminders = models.BooleanField(default=True)
    email_weekly_stats = models.BooleanField(default=True)
    email_inactivity_nudge = models.BooleanField(default=True)
    email_achievement_notifications = models.BooleanField(default=True)
    email_unsubscribed = models.BooleanField(default=False)  # Global unsubscribe
    unsubscribe_token = models.UUIDField(default=uuid.uuid4, editable=False)

    # Study statistics for streak tracking
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_study_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'User preferences'

    def __str__(self):
        return f"Preferences for {self.user.username}"

    def update_streak(self):
        """Update streak based on current date and last study date."""
        today = timezone.now().date()

        if self.last_study_date is None:
            # First study session
            self.current_streak = 1
            self.last_study_date = today
        elif self.last_study_date == today:
            # Already studied today, no change needed
            pass
        elif self.last_study_date == today - timezone.timedelta(days=1):
            # Studied yesterday, extend streak
            self.current_streak += 1
            self.last_study_date = today
        else:
            # Streak broken, start fresh
            self.current_streak = 1
            self.last_study_date = today

        # Update longest streak if current is higher
        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak

        self.save()

    def check_streak_at_risk(self):
        """Check if user's streak is at risk (hasn't studied today)."""
        if self.current_streak == 0:
            return False

        today = timezone.now().date()
        return self.last_study_date != today


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


class EmailLog(models.Model):
    """Log of sent emails for deduplication and history."""

    class EmailType(models.TextChoices):
        VERIFICATION = 'verification', 'Email Verification'
        STUDY_REMINDER = 'study_reminder', 'Study Reminder'
        STREAK_REMINDER = 'streak_reminder', 'Streak Reminder'
        WEEKLY_STATS = 'weekly_stats', 'Weekly Statistics'
        INACTIVITY_NUDGE = 'inactivity_nudge', 'Inactivity Nudge'
        ACHIEVEMENT = 'achievement', 'Achievement'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_logs')
    email_type = models.CharField(max_length=30, choices=EmailType.choices)
    subject = models.CharField(max_length=200)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['user', 'email_type', 'sent_at']),
        ]

    def __str__(self):
        return f"{self.email_type} to {self.user.username} at {self.sent_at}"

    @classmethod
    def was_sent_today(cls, user, email_type):
        """Check if this email type was already sent to user today."""
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return cls.objects.filter(
            user=user,
            email_type=email_type,
            sent_at__gte=today_start
        ).exists()

    @classmethod
    def was_sent_this_week(cls, user, email_type):
        """Check if this email type was already sent to user this week."""
        from datetime import timedelta
        week_ago = timezone.now() - timedelta(days=7)
        return cls.objects.filter(
            user=user,
            email_type=email_type,
            sent_at__gte=week_ago
        ).exists()


class CommandExecutionLog(models.Model):
    """Log of management command executions for monitoring and debugging."""

    class Status(models.TextChoices):
        STARTED = 'started', 'Started'
        SUCCESS = 'success', 'Success'
        FAILURE = 'failure', 'Failure'

    command_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status.choices)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    users_processed = models.IntegerField(default=0)
    emails_sent = models.IntegerField(default=0)
    errors_count = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['command_name', 'started_at']),
        ]

    def __str__(self):
        return f"{self.command_name} at {self.started_at} ({self.status})"

    @classmethod
    def start(cls, command_name):
        """Create a new log entry when command starts."""
        return cls.objects.create(
            command_name=command_name,
            status=cls.Status.STARTED,
            started_at=timezone.now(),
        )

    def finish_success(self, users_processed=0, emails_sent=0, details=None):
        """Mark command as successfully completed."""
        self.status = self.Status.SUCCESS
        self.finished_at = timezone.now()
        self.users_processed = users_processed
        self.emails_sent = emails_sent
        if details:
            self.details = details
        self.save()

    def finish_failure(self, error_message, errors_count=1, details=None):
        """Mark command as failed."""
        self.status = self.Status.FAILURE
        self.finished_at = timezone.now()
        self.error_message = error_message
        self.errors_count = errors_count
        if details:
            self.details = details
        self.save()

    @classmethod
    def get_last_run(cls, command_name):
        """Get the most recent execution of a command."""
        return cls.objects.filter(command_name=command_name).first()

    @classmethod
    def get_last_success(cls, command_name):
        """Get the most recent successful execution of a command."""
        return cls.objects.filter(
            command_name=command_name,
            status=cls.Status.SUCCESS
        ).first()
