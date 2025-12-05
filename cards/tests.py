"""
Unit tests for the flashcard application.

Test organization:
- SRSTests: Pure function tests for the SM-2 algorithm
- ClozeTests: Pure function tests for cloze parsing/rendering
- ModelTests: Django model tests for Card, Deck, ReviewLog
"""

from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from . import srs
from . import cloze
from .models import Deck, Card, ReviewLog


# =============================================================================
# SRS Algorithm Tests
# =============================================================================

class SRSEaseFactorTests(TestCase):
    """Tests for ease factor calculation."""

    def test_perfect_response_increases_ease(self):
        """Quality 5 (perfect) should increase ease factor."""
        new_ease = srs.calculate_ease_factor(2.5, quality=5)
        self.assertGreater(new_ease, 2.5)

    def test_good_response_maintains_ease(self):
        """Quality 4 (good) is neutral - maintains ease factor."""
        new_ease = srs.calculate_ease_factor(2.5, quality=4)
        self.assertEqual(new_ease, 2.5)

    def test_hard_response_maintains_ease(self):
        """Quality 3 (hard but correct) should slightly decrease ease."""
        new_ease = srs.calculate_ease_factor(2.5, quality=3)
        self.assertLess(new_ease, 2.5)

    def test_wrong_response_decreases_ease(self):
        """Quality 0-2 (wrong) should decrease ease factor."""
        for quality in [0, 1, 2]:
            new_ease = srs.calculate_ease_factor(2.5, quality=quality)
            self.assertLess(new_ease, 2.5, f"Quality {quality} should decrease ease")

    def test_ease_never_below_minimum(self):
        """Ease factor should never go below MIN_EASE_FACTOR (1.3)."""
        # Start with minimum and give worst rating repeatedly
        ease = srs.MIN_EASE_FACTOR
        for _ in range(10):
            ease = srs.calculate_ease_factor(ease, quality=0)
        self.assertGreaterEqual(ease, srs.MIN_EASE_FACTOR)

    def test_ease_factor_formula_accuracy(self):
        """Test the SM-2 ease factor formula directly."""
        # EF' = EF + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))
        # For quality=5: adjustment = 0.1 - 0 = 0.1
        new_ease = srs.calculate_ease_factor(2.5, quality=5)
        self.assertAlmostEqual(new_ease, 2.6, places=2)

        # For quality=0: adjustment = 0.1 - 5*(0.08 + 5*0.02) = 0.1 - 0.9 = -0.8
        new_ease = srs.calculate_ease_factor(2.5, quality=0)
        self.assertAlmostEqual(new_ease, 1.7, places=2)


class SRSIntervalTests(TestCase):
    """Tests for interval calculation."""

    def test_first_successful_review(self):
        """First successful review should give 1 day interval."""
        interval, reps = srs.calculate_interval(
            current_interval=0, repetitions=0, ease_factor=2.5, quality=4
        )
        self.assertEqual(interval, srs.FIRST_INTERVAL)  # 1 day
        self.assertEqual(reps, 1)

    def test_second_successful_review(self):
        """Second successful review should give 6 day interval."""
        interval, reps = srs.calculate_interval(
            current_interval=1, repetitions=1, ease_factor=2.5, quality=4
        )
        self.assertEqual(interval, srs.SECOND_INTERVAL)  # 6 days
        self.assertEqual(reps, 2)

    def test_subsequent_review_uses_ease_factor(self):
        """Third+ review should multiply interval by ease factor."""
        interval, reps = srs.calculate_interval(
            current_interval=6, repetitions=2, ease_factor=2.5, quality=4
        )
        self.assertEqual(interval, 15)  # 6 * 2.5 = 15
        self.assertEqual(reps, 3)

    def test_failed_review_resets_progress(self):
        """Failed review (quality < 3) should reset to learning phase."""
        for quality in [0, 1, 2]:
            interval, reps = srs.calculate_interval(
                current_interval=30, repetitions=5, ease_factor=2.5, quality=quality
            )
            self.assertEqual(interval, 1, f"Quality {quality} should reset interval")
            self.assertEqual(reps, 0, f"Quality {quality} should reset repetitions")

    def test_boundary_quality_3_is_success(self):
        """Quality 3 (hard but correct) counts as successful review."""
        interval, reps = srs.calculate_interval(
            current_interval=0, repetitions=0, ease_factor=2.5, quality=3
        )
        self.assertEqual(reps, 1)  # Should increment


class SRSCalculateReviewTests(TestCase):
    """Integration tests for the main calculate_review function."""

    def test_returns_review_result(self):
        """Should return a ReviewResult dataclass."""
        result = srs.calculate_review(
            current_ease=2.5,
            current_interval=0,
            repetitions=0,
            quality=4
        )
        self.assertIsInstance(result, srs.ReviewResult)
        self.assertIsInstance(result.ease_factor, float)
        self.assertIsInstance(result.interval, int)
        self.assertIsInstance(result.repetitions, int)
        self.assertIsInstance(result.next_review, datetime)

    def test_invalid_quality_raises_error(self):
        """Quality outside 0-5 should raise ValueError."""
        with self.assertRaises(ValueError):
            srs.calculate_review(2.5, 0, 0, quality=-1)
        with self.assertRaises(ValueError):
            srs.calculate_review(2.5, 0, 0, quality=6)

    def test_next_review_calculation(self):
        """Next review should be interval days from review_time."""
        review_time = datetime(2025, 1, 1, 12, 0, 0)
        result = srs.calculate_review(
            current_ease=2.5,
            current_interval=0,
            repetitions=0,
            quality=4,
            review_time=review_time
        )
        expected = review_time + timedelta(days=1)
        self.assertEqual(result.next_review, expected)

    def test_complete_learning_progression(self):
        """Simulate a card going through learning phase."""
        ease = 2.5
        interval = 0
        reps = 0

        # First review - quality 4
        result = srs.calculate_review(ease, interval, reps, quality=4)
        self.assertEqual(result.interval, 1)
        self.assertEqual(result.repetitions, 1)

        # Second review - quality 4
        result = srs.calculate_review(
            result.ease_factor, result.interval, result.repetitions, quality=4
        )
        self.assertEqual(result.interval, 6)
        self.assertEqual(result.repetitions, 2)

        # Third review - quality 4
        result = srs.calculate_review(
            result.ease_factor, result.interval, result.repetitions, quality=4
        )
        self.assertGreater(result.interval, 6)
        self.assertEqual(result.repetitions, 3)


class SRSEstimateRetentionTests(TestCase):
    """Tests for retention estimation."""

    def test_retention_in_valid_range(self):
        """Retention should be between 0 and 1."""
        retention = srs.estimate_retention(interval=10, ease_factor=2.5)
        self.assertGreater(retention, 0)
        self.assertLessEqual(retention, 1)

    def test_higher_ease_gives_better_retention(self):
        """Cards with higher ease factor should have better retention."""
        low_ease_retention = srs.estimate_retention(10, ease_factor=1.5)
        high_ease_retention = srs.estimate_retention(10, ease_factor=2.5)
        self.assertGreater(high_ease_retention, low_ease_retention)


# =============================================================================
# Cloze Module Tests
# =============================================================================

class ClozeParseTests(TestCase):
    """Tests for cloze parsing."""

    def test_parse_simple_cloze(self):
        """Parse basic {{c1::text}} syntax."""
        matches = cloze.parse_cloze("The {{c1::capital}} of France is Paris.")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].number, 1)
        self.assertEqual(matches[0].answer, "capital")
        self.assertIsNone(matches[0].hint)

    def test_parse_cloze_with_hint(self):
        """Parse {{c1::text::hint}} syntax."""
        matches = cloze.parse_cloze("The {{c1::cat::animal}} sat on the mat.")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].answer, "cat")
        self.assertEqual(matches[0].hint, "animal")

    def test_parse_multiple_clozes(self):
        """Parse multiple cloze deletions."""
        text = "{{c1::One}} and {{c2::Two}} and {{c3::Three}}"
        matches = cloze.parse_cloze(text)
        self.assertEqual(len(matches), 3)
        self.assertEqual([m.number for m in matches], [1, 2, 3])

    def test_parse_same_number_multiple_times(self):
        """Same cloze number can appear multiple times."""
        text = "{{c1::A}} is related to {{c1::B}}"
        matches = cloze.parse_cloze(text)
        self.assertEqual(len(matches), 2)
        self.assertTrue(all(m.number == 1 for m in matches))

    def test_parse_empty_string(self):
        """Empty string returns empty list."""
        matches = cloze.parse_cloze("")
        self.assertEqual(matches, [])

    def test_parse_no_cloze(self):
        """String without cloze returns empty list."""
        matches = cloze.parse_cloze("Just regular text.")
        self.assertEqual(matches, [])


class ClozeGetNumbersTests(TestCase):
    """Tests for getting unique cloze numbers."""

    def test_get_unique_numbers(self):
        """Should return unique cloze numbers."""
        text = "{{c1::A}} {{c2::B}} {{c1::C}} {{c3::D}}"
        numbers = cloze.get_cloze_numbers(text)
        self.assertEqual(numbers, {1, 2, 3})

    def test_get_numbers_empty(self):
        """No cloze returns empty set."""
        numbers = cloze.get_cloze_numbers("No cloze here")
        self.assertEqual(numbers, set())


class ClozeRenderQuestionTests(TestCase):
    """Tests for rendering cloze questions."""

    def test_render_simple_blank(self):
        """Render cloze as [...] blank."""
        result = cloze.render_cloze_question("The {{c1::answer}} is here.")
        self.assertEqual(result, "The [...] is here.")

    def test_render_with_hint(self):
        """Render cloze with hint as [hint]."""
        result = cloze.render_cloze_question("The {{c1::cat::animal}} sat.")
        self.assertEqual(result, "The [animal] sat.")

    def test_render_active_number_only(self):
        """Only blank the active cloze number."""
        text = "{{c1::One}} and {{c2::Two}}"
        result = cloze.render_cloze_question(text, active_number=1)
        self.assertEqual(result, "[...] and Two")

    def test_render_active_number_reveals_others(self):
        """Inactive clozes show their answers."""
        text = "{{c1::One}} and {{c2::Two}}"
        result = cloze.render_cloze_question(text, active_number=2)
        self.assertEqual(result, "One and [...]")

    def test_render_all_when_no_active(self):
        """All clozes blanked when active_number is None."""
        text = "{{c1::One}} and {{c2::Two}}"
        result = cloze.render_cloze_question(text, active_number=None)
        self.assertEqual(result, "[...] and [...]")


class ClozeRenderAnswerTests(TestCase):
    """Tests for rendering cloze answers."""

    def test_render_reveals_answer(self):
        """Answer should show the text."""
        result = cloze.render_cloze_answer("The {{c1::answer}} is here.")
        self.assertEqual(result, "The answer is here.")

    def test_render_active_highlighted(self):
        """Active cloze should be highlighted with **."""
        text = "{{c1::One}} and {{c2::Two}}"
        result = cloze.render_cloze_answer(text, active_number=1)
        self.assertEqual(result, "**One** and Two")


class ClozeValidationTests(TestCase):
    """Tests for cloze validation."""

    def test_valid_cloze(self):
        """Valid cloze should return True."""
        self.assertTrue(cloze.is_valid_cloze("{{c1::test}}"))
        self.assertTrue(cloze.is_valid_cloze("{{c1::test::hint}}"))
        self.assertTrue(cloze.is_valid_cloze("Text {{c1::test}} more text"))

    def test_invalid_cloze(self):
        """Invalid/missing cloze should return False."""
        self.assertFalse(cloze.is_valid_cloze("No cloze here"))
        self.assertFalse(cloze.is_valid_cloze(""))
        self.assertFalse(cloze.is_valid_cloze("{{c1:missing colon}}"))

    def test_validate_syntax_valid(self):
        """Valid syntax returns empty error list."""
        errors = cloze.validate_cloze_syntax("{{c1::test}}")
        self.assertEqual(errors, [])

    def test_validate_syntax_no_cloze(self):
        """No cloze returns error."""
        errors = cloze.validate_cloze_syntax("No cloze here")
        self.assertEqual(len(errors), 1)
        self.assertIn("No valid cloze", errors[0])

    def test_validate_syntax_mismatched_braces(self):
        """Mismatched braces returns error."""
        errors = cloze.validate_cloze_syntax("{{c1::test} missing brace {{c2::ok}}")
        self.assertTrue(any("braces" in e.lower() for e in errors))


class ClozeExtractAnswersTests(TestCase):
    """Tests for extracting cloze answers."""

    def test_extract_single(self):
        """Extract single answer."""
        answers = cloze.extract_cloze_answers("{{c1::answer}}")
        self.assertEqual(answers, ["answer"])

    def test_extract_multiple(self):
        """Extract multiple answers in order."""
        answers = cloze.extract_cloze_answers("{{c1::one}} {{c2::two}}")
        self.assertEqual(answers, ["one", "two"])


# =============================================================================
# Model Tests
# =============================================================================

class DeckModelTests(TestCase):
    """Tests for the Deck model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.deck = Deck.objects.create(
            name='Test Deck',
            owner=self.user
        )

    def test_deck_creation(self):
        """Deck should be created with correct attributes."""
        self.assertEqual(self.deck.name, 'Test Deck')
        self.assertEqual(self.deck.owner, self.user)

    def test_deck_str(self):
        """Deck string representation is the name."""
        self.assertEqual(str(self.deck), 'Test Deck')

    def test_cards_due_count_no_cards(self):
        """Empty deck has 0 due cards."""
        self.assertEqual(self.deck.cards_due_count(), 0)

    def test_cards_due_count_with_due_cards(self):
        """Count only cards that are due."""
        # Due card (next_review in past)
        Card.objects.create(
            deck=self.deck,
            front='Due card',
            next_review=timezone.now() - timedelta(days=1)
        )
        # Not due card (next_review in future)
        Card.objects.create(
            deck=self.deck,
            front='Not due card',
            next_review=timezone.now() + timedelta(days=1)
        )
        self.assertEqual(self.deck.cards_due_count(), 1)


class CardModelTests(TestCase):
    """Tests for the Card model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.deck = Deck.objects.create(name='Test Deck', owner=self.user)
        self.card = Card.objects.create(
            deck=self.deck,
            front='What is 2+2?',
            back='4'
        )

    def test_card_creation_defaults(self):
        """Card should have correct SRS defaults."""
        self.assertEqual(self.card.ease_factor, 2.5)
        self.assertEqual(self.card.interval, 0)
        self.assertEqual(self.card.repetitions, 0)
        self.assertEqual(self.card.card_type, Card.CardType.BASIC)

    def test_card_str_truncates(self):
        """Card string representation truncates long text."""
        long_card = Card.objects.create(
            deck=self.deck,
            front='A' * 100
        )
        self.assertTrue(str(long_card).endswith('...'))
        self.assertLessEqual(len(str(long_card)), 54)  # 50 chars + "..."

    def test_is_due_when_past(self):
        """Card is due when next_review is in the past."""
        self.card.next_review = timezone.now() - timedelta(hours=1)
        self.card.save()
        self.assertTrue(self.card.is_due())

    def test_is_due_when_now(self):
        """Card is due when next_review is now."""
        self.card.next_review = timezone.now()
        self.card.save()
        self.assertTrue(self.card.is_due())

    def test_is_not_due_when_future(self):
        """Card is not due when next_review is in the future."""
        self.card.next_review = timezone.now() + timedelta(hours=1)
        self.card.save()
        self.assertFalse(self.card.is_due())

    def test_review_updates_card_state(self):
        """Review should update card's SRS fields."""
        original_ease = self.card.ease_factor
        self.card.review(quality=5)  # Use quality=5 to see ease factor change

        self.card.refresh_from_db()
        self.assertGreater(self.card.ease_factor, original_ease)
        self.assertEqual(self.card.repetitions, 1)
        self.assertEqual(self.card.interval, 1)
        self.assertIsNotNone(self.card.last_reviewed)

    def test_review_creates_log(self):
        """Review should create a ReviewLog entry."""
        log = self.card.review(quality=4)

        self.assertIsInstance(log, ReviewLog)
        self.assertEqual(log.card, self.card)
        self.assertEqual(log.quality, 4)
        self.assertEqual(log.ease_factor_before, 2.5)

    def test_review_failed_resets_progress(self):
        """Failed review resets card to learning phase."""
        # First build up some progress
        self.card.review(quality=4)  # rep 1
        self.card.review(quality=4)  # rep 2
        self.card.refresh_from_db()
        self.assertEqual(self.card.repetitions, 2)

        # Now fail
        self.card.review(quality=2)
        self.card.refresh_from_db()
        self.assertEqual(self.card.repetitions, 0)
        self.assertEqual(self.card.interval, 1)


class ReviewLogModelTests(TestCase):
    """Tests for the ReviewLog model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.deck = Deck.objects.create(name='Test Deck', owner=self.user)
        self.card = Card.objects.create(
            deck=self.deck,
            front='Test',
            back='Test'
        )

    def test_review_log_created_on_review(self):
        """ReviewLog should be created when card is reviewed."""
        initial_count = ReviewLog.objects.count()
        self.card.review(quality=4)
        self.assertEqual(ReviewLog.objects.count(), initial_count + 1)

    def test_review_log_tracks_changes(self):
        """ReviewLog should track before/after values."""
        log = self.card.review(quality=5)  # Use quality=5 to see ease factor change

        self.assertEqual(log.ease_factor_before, 2.5)
        self.assertGreater(log.ease_factor_after, log.ease_factor_before)
        self.assertEqual(log.interval_before, 0)
        self.assertEqual(log.interval_after, 1)

    def test_multiple_reviews_create_multiple_logs(self):
        """Each review creates a separate log entry."""
        self.card.review(quality=4)
        self.card.review(quality=5)
        self.card.review(quality=3)

        logs = ReviewLog.objects.filter(card=self.card)
        self.assertEqual(logs.count(), 3)


# =============================================================================
# Form Tests
# =============================================================================

from .forms import (
    StyledFormMixin, LoginForm, RegisterForm,
    DeckForm, CardForm, UserPreferencesForm, ReviewReminderForm
)


class StyledFormMixinTests(TestCase):
    """Tests for the StyledFormMixin CSS class application."""

    def test_text_input_gets_styled(self):
        """Text inputs should get Tailwind classes."""
        form = DeckForm()
        self.assertIn('rounded-md', form.fields['name'].widget.attrs['class'])
        self.assertIn('border-gray-300', form.fields['name'].widget.attrs['class'])

    def test_textarea_gets_styled(self):
        """Textareas should get Tailwind classes and rows attribute."""
        form = DeckForm()
        self.assertIn('rounded-md', form.fields['description'].widget.attrs['class'])
        self.assertEqual(form.fields['description'].widget.attrs['rows'], 3)

    def test_select_gets_styled(self):
        """Select fields should get Tailwind classes."""
        form = CardForm()
        self.assertIn('rounded-md', form.fields['card_type'].widget.attrs['class'])

    def test_checkbox_gets_different_style(self):
        """Checkbox inputs should get checkbox-specific classes."""
        form = ReviewReminderForm()
        checkbox_class = form.fields['enabled'].widget.attrs['class']
        self.assertIn('h-4', checkbox_class)
        self.assertIn('w-4', checkbox_class)
        self.assertNotIn('block w-full', checkbox_class)


class RegisterFormTests(TestCase):
    """Tests for user registration form."""

    def test_valid_registration(self):
        """Valid data should pass validation."""
        form = RegisterForm(data={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
        })
        self.assertTrue(form.is_valid())

    def test_email_required(self):
        """Email field should be required."""
        form = RegisterForm(data={
            'username': 'newuser',
            'email': '',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_password_mismatch(self):
        """Mismatched passwords should fail validation."""
        form = RegisterForm(data={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'SecurePass123!',
            'password2': 'DifferentPass456!',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_invalid_email(self):
        """Invalid email format should fail validation."""
        form = RegisterForm(data={
            'username': 'newuser',
            'email': 'not-an-email',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)


class DeckFormTests(TestCase):
    """Tests for deck creation/edit form."""

    def test_valid_deck(self):
        """Valid deck data should pass validation."""
        form = DeckForm(data={
            'name': 'My Deck',
            'description': 'A test deck',
        })
        self.assertTrue(form.is_valid())

    def test_name_required(self):
        """Deck name should be required."""
        form = DeckForm(data={
            'name': '',
            'description': 'A test deck',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_description_optional(self):
        """Deck description should be optional."""
        form = DeckForm(data={
            'name': 'My Deck',
            'description': '',
        })
        self.assertTrue(form.is_valid())


class CardFormTests(TestCase):
    """Tests for card creation/edit form with cloze validation."""

    def test_valid_basic_card(self):
        """Valid basic card should pass validation."""
        form = CardForm(data={
            'card_type': 'basic',
            'front': 'What is 2+2?',
            'back': '4',
            'notes': '',
        })
        self.assertTrue(form.is_valid())

    def test_valid_cloze_card(self):
        """Valid cloze card should pass validation."""
        form = CardForm(data={
            'card_type': 'cloze',
            'front': 'The {{c1::capital}} of France is Paris.',
            'back': '',
            'notes': '',
        })
        self.assertTrue(form.is_valid())

    def test_valid_cloze_with_hint(self):
        """Cloze with hint should pass validation."""
        form = CardForm(data={
            'card_type': 'cloze',
            'front': 'The {{c1::cat::animal}} sat on the mat.',
            'back': '',
            'notes': '',
        })
        self.assertTrue(form.is_valid())

    def test_cloze_without_deletion_fails(self):
        """Cloze card without cloze syntax should fail."""
        form = CardForm(data={
            'card_type': 'cloze',
            'front': 'This has no cloze deletion.',
            'back': '',
            'notes': '',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('front', form.errors)
        self.assertTrue(any('No valid cloze' in e for e in form.errors['front']))

    def test_cloze_malformed_syntax_fails(self):
        """Cloze card with malformed syntax should fail."""
        form = CardForm(data={
            'card_type': 'cloze',
            'front': 'This has {{c1:single colon}} syntax.',
            'back': '',
            'notes': '',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('front', form.errors)

    def test_basic_card_ignores_cloze_validation(self):
        """Basic cards should not require cloze syntax."""
        form = CardForm(data={
            'card_type': 'basic',
            'front': 'No cloze here, and that is fine.',
            'back': 'Answer',
            'notes': '',
        })
        self.assertTrue(form.is_valid())

    def test_front_required(self):
        """Card front should be required."""
        form = CardForm(data={
            'card_type': 'basic',
            'front': '',
            'back': 'Answer',
            'notes': '',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('front', form.errors)


class UserPreferencesFormTests(TestCase):
    """Tests for user preferences form."""

    def test_valid_preferences(self):
        """Valid preferences should pass validation."""
        form = UserPreferencesForm(data={
            'theme': 'dark',
            'card_text_size': 'large',
            'cards_per_session': 20,
        })
        self.assertTrue(form.is_valid())

    def test_invalid_theme_choice(self):
        """Invalid theme choice should fail."""
        form = UserPreferencesForm(data={
            'theme': 'invalid_theme',
            'card_text_size': 'large',
            'cards_per_session': 20,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('theme', form.errors)

    def test_all_theme_choices_valid(self):
        """All defined theme choices should be valid."""
        for theme in ['light', 'dark', 'system']:
            form = UserPreferencesForm(data={
                'theme': theme,
                'card_text_size': 'medium',
                'cards_per_session': 15,
            })
            self.assertTrue(form.is_valid(), f"Theme '{theme}' should be valid")

    def test_all_text_size_choices_valid(self):
        """All defined text size choices should be valid."""
        for size in ['small', 'medium', 'large', 'xlarge', 'xxlarge', 'xxxlarge']:
            form = UserPreferencesForm(data={
                'theme': 'system',
                'card_text_size': size,
                'cards_per_session': 10,
            })
            self.assertTrue(form.is_valid(), f"Text size '{size}' should be valid")


class ReviewReminderFormTests(TestCase):
    """Tests for review reminder settings form."""

    def test_valid_reminder(self):
        """Valid reminder settings should pass validation."""
        form = ReviewReminderForm(data={
            'enabled': True,
            'frequency': 'daily',
            'preferred_time': '09:00',
            'custom_days': '0,1,2,3,4',
        })
        self.assertTrue(form.is_valid())

    def test_disabled_reminder(self):
        """Disabled reminder should be valid."""
        form = ReviewReminderForm(data={
            'enabled': False,
            'frequency': 'daily',
            'preferred_time': '09:00',
            'custom_days': '',
        })
        self.assertTrue(form.is_valid())

    def test_all_frequency_choices_valid(self):
        """All frequency choices should be valid."""
        for freq in ['daily', 'weekly', 'custom']:
            form = ReviewReminderForm(data={
                'enabled': True,
                'frequency': freq,
                'preferred_time': '08:00',
                'custom_days': '0,2,4',
            })
            self.assertTrue(form.is_valid(), f"Frequency '{freq}' should be valid")


# =============================================================================
# View Tests
# =============================================================================

from django.test import Client
from django.urls import reverse
import json


class AuthViewTests(TestCase):
    """Tests for authentication views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_login_page_loads(self):
        """Login page should load for anonymous users."""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign in')

    def test_login_redirects_authenticated_user(self):
        """Authenticated users should be redirected from login page."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('login'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_login_success(self):
        """Valid credentials should log user in."""
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'testpass123',
        })
        self.assertRedirects(response, reverse('dashboard'))

    def test_login_failure(self):
        """Invalid credentials should show error."""
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter a correct username')

    def test_register_page_loads(self):
        """Register page should load for anonymous users."""
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    def test_register_redirects_authenticated_user(self):
        """Authenticated users should be redirected from register page."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('register'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_register_success(self):
        """Valid registration should create user and log them in."""
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
        })
        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_logout(self):
        """Logout should redirect to login page."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'))


class DashboardViewTests(TestCase):
    """Tests for dashboard view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.deck = Deck.objects.create(name='Test Deck', owner=self.user)

    def test_dashboard_requires_login(self):
        """Dashboard should redirect anonymous users to login."""
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")

    def test_dashboard_loads_for_authenticated_user(self):
        """Dashboard should load for authenticated users."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_shows_deck_stats(self):
        """Dashboard should show deck information."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Test Deck')

    def test_dashboard_shows_due_cards(self):
        """Dashboard should show cards due for review."""
        Card.objects.create(
            deck=self.deck,
            front='Test card',
            next_review=timezone.now() - timedelta(hours=1)
        )
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, '1')  # 1 card due


class DeckViewTests(TestCase):
    """Tests for deck CRUD views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser', password='testpass123'
        )
        self.deck = Deck.objects.create(
            name='My Deck',
            description='Test description',
            owner=self.user
        )
        self.client.login(username='testuser', password='testpass123')

    def test_deck_list_view(self):
        """Deck list should show user's decks."""
        response = self.client.get(reverse('deck_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Deck')

    def test_deck_list_excludes_other_users_decks(self):
        """Deck list should not show other users' decks."""
        Deck.objects.create(name='Other Deck', owner=self.other_user)
        response = self.client.get(reverse('deck_list'))
        self.assertNotContains(response, 'Other Deck')

    def test_deck_create_view_get(self):
        """Deck create form should load."""
        response = self.client.get(reverse('deck_create'))
        self.assertEqual(response.status_code, 200)

    def test_deck_create_view_post(self):
        """Valid POST should create deck."""
        response = self.client.post(reverse('deck_create'), {
            'name': 'New Deck',
            'description': 'New description',
        })
        self.assertRedirects(response, reverse('deck_list'))
        self.assertTrue(Deck.objects.filter(name='New Deck', owner=self.user).exists())

    def test_deck_update_view_get(self):
        """Deck update form should load."""
        response = self.client.get(reverse('deck_update', kwargs={'pk': self.deck.pk}))
        self.assertEqual(response.status_code, 200)

    def test_deck_update_view_post(self):
        """Valid POST should update deck."""
        response = self.client.post(reverse('deck_update', kwargs={'pk': self.deck.pk}), {
            'name': 'Updated Name',
            'description': 'Updated description',
        })
        self.assertRedirects(response, reverse('deck_list'))
        self.deck.refresh_from_db()
        self.assertEqual(self.deck.name, 'Updated Name')

    def test_deck_delete_view_get(self):
        """Deck delete confirmation should load."""
        response = self.client.get(reverse('deck_delete', kwargs={'pk': self.deck.pk}))
        self.assertEqual(response.status_code, 200)

    def test_deck_delete_view_post(self):
        """POST should delete deck."""
        response = self.client.post(reverse('deck_delete', kwargs={'pk': self.deck.pk}))
        self.assertRedirects(response, reverse('deck_list'))
        self.assertFalse(Deck.objects.filter(pk=self.deck.pk).exists())

    def test_deck_detail_view(self):
        """Deck detail should show deck info and cards."""
        Card.objects.create(deck=self.deck, front='Test Q', back='Test A')
        response = self.client.get(reverse('deck_detail', kwargs={'pk': self.deck.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Deck')
        self.assertContains(response, 'Test Q')

    def test_cannot_access_other_users_deck(self):
        """Users cannot access other users' deck details."""
        other_deck = Deck.objects.create(name='Other', owner=self.other_user)
        response = self.client.get(reverse('deck_detail', kwargs={'pk': other_deck.pk}))
        self.assertEqual(response.status_code, 404)

    def test_deck_export(self):
        """Deck export should return JSON file."""
        Card.objects.create(deck=self.deck, front='Q1', back='A1')
        response = self.client.get(reverse('deck_export', kwargs={'pk': self.deck.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = json.loads(response.content)
        self.assertEqual(data['name'], 'My Deck')
        self.assertEqual(len(data['cards']), 1)

    def test_deck_import_get(self):
        """Deck import page should load."""
        response = self.client.get(reverse('deck_import'))
        self.assertEqual(response.status_code, 200)


class CardViewTests(TestCase):
    """Tests for card CRUD views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.deck = Deck.objects.create(name='Test Deck', owner=self.user)
        self.card = Card.objects.create(
            deck=self.deck,
            front='Test Question',
            back='Test Answer'
        )
        self.client.login(username='testuser', password='testpass123')

    def test_card_create_view_get(self):
        """Card create form should load."""
        response = self.client.get(reverse('card_create', kwargs={'deck_pk': self.deck.pk}))
        self.assertEqual(response.status_code, 200)

    def test_card_create_view_post(self):
        """Valid POST should create card."""
        response = self.client.post(reverse('card_create', kwargs={'deck_pk': self.deck.pk}), {
            'card_type': 'basic',
            'front': 'New Question',
            'back': 'New Answer',
            'notes': '',
        })
        self.assertRedirects(response, reverse('deck_detail', kwargs={'pk': self.deck.pk}))
        self.assertTrue(Card.objects.filter(front='New Question').exists())

    def test_card_update_view_get(self):
        """Card update form should load."""
        response = self.client.get(reverse('card_update', kwargs={'pk': self.card.pk}))
        self.assertEqual(response.status_code, 200)

    def test_card_update_view_post(self):
        """Valid POST should update card."""
        response = self.client.post(reverse('card_update', kwargs={'pk': self.card.pk}), {
            'card_type': 'basic',
            'front': 'Updated Question',
            'back': 'Updated Answer',
            'notes': '',
        })
        self.assertRedirects(response, reverse('deck_detail', kwargs={'pk': self.deck.pk}))
        self.card.refresh_from_db()
        self.assertEqual(self.card.front, 'Updated Question')

    def test_card_delete_view_get(self):
        """Card delete confirmation should load."""
        response = self.client.get(reverse('card_delete', kwargs={'pk': self.card.pk}))
        self.assertEqual(response.status_code, 200)

    def test_card_delete_view_post(self):
        """POST should delete card."""
        response = self.client.post(reverse('card_delete', kwargs={'pk': self.card.pk}))
        self.assertRedirects(response, reverse('deck_detail', kwargs={'pk': self.deck.pk}))
        self.assertFalse(Card.objects.filter(pk=self.card.pk).exists())


class ReviewViewTests(TestCase):
    """Tests for review session views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        from .models import UserPreferences
        UserPreferences.objects.create(user=self.user)
        self.deck = Deck.objects.create(name='Test Deck', owner=self.user)
        self.card = Card.objects.create(
            deck=self.deck,
            front='Test Question',
            back='Test Answer',
            next_review=timezone.now() - timedelta(hours=1)  # Due now
        )
        self.client.login(username='testuser', password='testpass123')

    def test_review_session_loads(self):
        """Review session should load with due cards."""
        response = self.client.get(reverse('review_session'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Question')

    def test_review_session_redirects_when_no_cards_due(self):
        """Review session should redirect when no cards are due."""
        self.card.next_review = timezone.now() + timedelta(days=1)
        self.card.save()
        response = self.client.get(reverse('review_session'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_review_deck_specific(self):
        """Review can be limited to specific deck."""
        response = self.client.get(reverse('review_deck', kwargs={'deck_pk': self.deck.pk}))
        self.assertEqual(response.status_code, 200)

    def test_review_card_api(self):
        """Review card API should update card and return JSON."""
        response = self.client.post(
            reverse('review_card', kwargs={'pk': self.card.pk}),
            data=json.dumps({'quality': 4}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('next_review', data)

    def test_review_card_api_invalid_quality(self):
        """Review card API should reject invalid quality."""
        response = self.client.post(
            reverse('review_card', kwargs={'pk': self.card.pk}),
            data=json.dumps({'quality': 10}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_review_card_api_invalid_json(self):
        """Review card API should reject invalid JSON."""
        response = self.client.post(
            reverse('review_card', kwargs={'pk': self.card.pk}),
            data='not json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)


class SettingsViewTests(TestCase):
    """Tests for settings views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        from .models import UserPreferences, ReviewReminder
        UserPreferences.objects.create(user=self.user)
        ReviewReminder.objects.create(user=self.user)
        self.client.login(username='testuser', password='testpass123')

    def test_settings_page_loads(self):
        """Settings page should load."""
        response = self.client.get(reverse('settings'))
        self.assertEqual(response.status_code, 200)

    def test_settings_update(self):
        """Settings can be updated via POST."""
        response = self.client.post(reverse('settings'), {
            'theme': 'dark',
            'card_text_size': 'xlarge',
            'cards_per_session': 30,
            'enabled': True,
            'frequency': 'daily',
            'preferred_time': '10:00',
            'custom_days': '0,1,2,3,4',
        })
        self.assertRedirects(response, reverse('settings'))


class ThemeAPITests(TestCase):
    """Tests for theme API endpoints."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        from .models import UserPreferences
        UserPreferences.objects.create(user=self.user)
        self.client.login(username='testuser', password='testpass123')

    def test_set_theme_api(self):
        """Theme can be set via API."""
        response = self.client.post(
            reverse('api_set_theme'),
            data=json.dumps({'theme': 'dark'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['theme'], 'dark')

    def test_set_theme_api_invalid_theme(self):
        """Invalid theme should be rejected."""
        response = self.client.post(
            reverse('api_set_theme'),
            data=json.dumps({'theme': 'invalid'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_set_theme_api_invalid_json(self):
        """Invalid JSON should be rejected."""
        response = self.client.post(
            reverse('api_set_theme'),
            data='not json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_get_theme_api(self):
        """Theme can be retrieved via API."""
        response = self.client.get(reverse('api_get_theme'))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('theme', data)
