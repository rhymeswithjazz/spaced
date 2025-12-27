# Flashcard Application Architecture

A Django-based flashcard application with SM-2 spaced repetition algorithm for optimal review scheduling.

## Overview

Full-featured flashcard learning application built with Django. Provides spaced repetition scheduling, deck/card management, email notifications, achievement tracking, and a modern responsive UI using TailwindCSS.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11 |
| Framework | Django 5.x |
| Database | SQLite (swappable to PostgreSQL) |
| Task Scheduling | Supercronic |
| Process Manager | SupervisorD |
| Container | Docker |
| Frontend | TailwindCSS (CDN), Alpine.js, canvas-confetti |
| Package Manager | uv |

## Project Structure

```
flashcard/
├── config/                     # Django project configuration
│   ├── __init__.py
│   ├── settings.py            # All settings with env variable support
│   ├── urls.py                # Root URL configuration
│   ├── asgi.py                # ASGI entry point
│   └── wsgi.py                # WSGI entry point
├── cards/                      # Main Django app
│   ├── __init__.py
│   ├── admin.py               # Admin configuration
│   ├── apps.py                # App configuration
│   ├── models.py              # All database models
│   ├── urls.py                # App URL routing
│   ├── views/                  # Organized view modules by feature
│   │   ├── __init__.py
│   │   ├── auth.py            # Login, register, email verification
│   │   ├── dashboard.py       # Main dashboard
│   │   ├── deck.py            # Deck CRUD operations
│   │   ├── card.py            # Card CRUD operations
│   │   ├── review.py          # Review session logic
│   │   ├── settings.py        # User settings
│   │   ├── email.py           # Email preferences management
│   │   └── health.py          # Health check endpoint
│   ├── management/commands/   # Scheduled tasks
│   │   ├── __init__.py
│   │   ├── send_reminders.py
│   │   ├── send_streak_reminders.py
│   │   ├── send_weekly_stats.py
│   │   ├── send_inactivity_nudges.py
│   │   ├── send_test_email.py
│   ├── templates/cards/       # App-specific templates
│   ├── migrations/            # Database migrations
│   ├── srs.py                 # SM-2 spaced repetition algorithm
│   ├── cloze.py               # Cloze deletion parsing
│   ├── email.py               # Email sending utilities
│   ├── achievements.py        # Achievement tracking system
│   ├── forms.py               # Form classes with styling
│   ├── context_processors.py  # Template context injection
│   ├── tests.py               # Test suite (121 tests, 92% coverage)
│   └── achievements.py
├── templates/                  # Shared templates
│   ├── base.html              # Base template with theme system
│   └── cards/                  # Email templates
│       └── email/
├── static/                     # Static files
│   ├── css/
│   │   ├── main.css
│   │   ├── landing.css
│   │   └── review.css
│   ├── js/
│   │   ├── app.js
│   │   ├── dashboard.js
│   │   ├── review.js
│   │   └── settings.js
│   └── images/
├── pyproject.toml             # Python dependencies
├── Dockerfile                 # Docker container
├── docker-compose.yml         # Docker services
├── crontab                    # Scheduled tasks
├── supervisord.conf           # Process manager config
├── entrypoint.sh              # Container entrypoint
└── README.md
```

## Database Schema

### User (Django Built-in)

Standard Django auth user with email verification.

### UserPreferences

One-to-one with User, stores all user settings.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| user | FK | - | Foreign key to User |
| theme | VARCHAR(10) | 'system' | light, dark, or system |
| card_text_size | VARCHAR(10) | 'large' | Text size for reviews |
| new_cards_per_day | INT | 20 | New cards limit per day |
| max_reviews_per_session | INT | 0 | 0 = unlimited |
| celebration_animations | BOOL | TRUE | Enable confetti |
| user_timezone | VARCHAR(50) | 'UTC' | User's timezone |
| email_* | BOOL | TRUE | Email preference flags |
| email_unsubscribed | BOOL | FALSE | Global unsubscribe |
| unsubscribe_token | UUID | - | For unsubscribe links |
| current_streak | INT | 0 | Current streak count |
| longest_streak | INT | 0 | Longest streak ever |
| last_study_date | DATE | NULL | Last review date |

### Deck

Flashcard decks owned by users.

| Field | Type | Description |
|-------|------|-------------|
| id | INT | Primary key |
| name | VARCHAR(200) | Deck name |
| description | TEXT | Optional description |
| owner | FK | Foreign key to User |
| created_at | DATETIME | Creation timestamp |
| updated_at | DATETIME | Last update timestamp |

### Card

Flashcards with SRS scheduling fields.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| id | INT | - | Primary key |
| deck | FK | - | Foreign key to Deck |
| card_type | VARCHAR(20) | - | basic, cloze, reverse, typein |
| front | TEXT | - | Front content (question) |
| back | TEXT | - | Back content (answer) |
| notes | TEXT | - | Optional notes |
| ease_factor | REAL | 2.5 | SM-2 ease factor |
| interval | INT | 0 | Days until next review |
| repetitions | INT | 0 | Successful review count |
| next_review | DATETIME | - | When card is due |
| last_reviewed | DATETIME | - | Last review timestamp |
| has_been_reviewed | BOOL | FALSE | Has been reviewed before |
| created_at | DATETIME | - | Creation timestamp |
| updated_at | DATETIME | - | Last update timestamp |

### ReviewLog

Tracks all review history for analytics.

| Field | Type | Description |
|-------|------|-------------|
| id | INT | Primary key |
| card | FK | Foreign key to Card |
| quality | INT | Rating 0-5 |
| ease_factor_before | REAL | EF before review |
| ease_factor_after | REAL | EF after review |
| interval_before | INT | Interval before review |
| interval_after | INT | Interval after review |
| reviewed_at | DATETIME | Review timestamp |

### ReviewReminder

User notification preferences.

| Field | Type | Description |
|-------|------|-------------|
| user | FK | Foreign key to User (unique) |
| enabled | BOOL | Reminders enabled |
| frequency | VARCHAR(20) | daily, weekly, custom |
| preferred_time | TIME | Preferred notification time |
| custom_days | VARCHAR(20) | Comma-separated days (0=Mon) |
| last_sent | DATETIME | Last reminder sent |

### EmailVerificationToken

Email verification tokens.

| Field | Type | Description |
|-------|------|-------------|
| user | FK | Foreign key to User (unique) |
| token | VARCHAR(64) | 64-char URL-safe token |
| created_at | DATETIME | Token creation time |

### EmailLog

Email sending history for deduplication.

| Field | Type | Description |
|-------|------|-------------|
| id | INT | Primary key |
| user | FK | Foreign key to User |
| email_type | VARCHAR(30) | Type of email sent |
| subject | VARCHAR(200) | Email subject |
| sent_at | DATETIME | Send timestamp |

### CommandExecutionLog

Tracks scheduled command runs.

| Field | Type | Description |
|-------|------|-------------|
| id | INT | Primary key |
| command_name | VARCHAR(100) | Command name |
| status | VARCHAR(20) | success, failed, partial |
| users_processed | INT | Users processed |
| emails_sent | INT | Emails sent |
| errors | TEXT | Error messages |
| executed_at | DATETIME | Execution timestamp |

## Spaced Repetition System (SM-2)

The application uses the SM-2 algorithm, originally developed for SuperMemo, implemented as pure functions in `cards/srs.py`.

### Quality Ratings (0-5)

| Rating | Label | Description |
|--------|-------|-------------|
| 0 | Again | Complete blackout, no recognition |
| 1 | Wrong-Easy | Wrong, but answer seemed easy |
| 2 | Wrong-Hard | Wrong, but remembered upon seeing |
| 3 | Hard | Correct, with significant difficulty |
| 4 | Good | Correct, with some hesitation |
| 5 | Easy | Perfect response, immediate recall |

### Core Formulas

**Ease Factor Calculation:**
```
EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
```

**Interval Calculation:**
- Quality < 3 (failed): interval = 1, repetitions = 0
- Quality >= 3 (passed):
  - First success: interval = 1 day
  - Second success: interval = 6 days
  - Subsequent: interval = previous_interval * ease_factor

### Constants

```python
MIN_EASE_FACTOR = 1.3       # Minimum ease factor
DEFAULT_EASE_FACTOR = 2.5  # Starting ease for new cards
FIRST_INTERVAL = 1         # First review after 1 day
SECOND_INTERVAL = 6        # Second review after 6 days
```

### Integration

```python
# cards/models.py - Card.review(quality)
result = srs.calculate_review(
    current_ease=self.ease_factor,
    current_interval=self.interval,
    repetitions=self.repetitions,
    quality=quality,
    review_time=timezone.now()
)

self.ease_factor = result.ease_factor
self.interval = result.interval
self.repetitions = result.repetitions
self.next_review = result.next_review
self.last_reviewed = timezone.now()
self.has_been_reviewed = True
self.save()
```

## Card Types

| Type | Description | Front/Back |
|------|-------------|------------|
| **basic** | Standard front/back card | Question / Answer |
| **cloze** | Text with fill-in-the-blank | Partial text / Full text |
| **reverse** | Both directions reviewed | Auto-generates paired card |
| **typein** | User types exact answer | Question / Expected answer |

### Cloze Deletion Syntax

```
{{c1::answer}}              # Simple cloze
{{c1::answer::hint}}        # Cloze with hint placeholder
{{c1::word1}} and {{c2::word2}}  # Multiple deletions
```

Multiple clozes in a card become separate review items.

### Type-in Cards

Type-in cards require exact text input (case-insensitive). Used for spelling practice or precise answer recall.

### Reverse Cards

Reverse cards automatically generate a paired card with front/back swapped. Both directions are scheduled independently using SRS.

## Review Session Flow

### Session Initiation

1. User clicks "Review" on dashboard or deck
2. View fetches due cards:
   - `next_review <= now`
   - `has_been_reviewed = True` (for new cards, shows in learning mode)

### Card Selection

1. Get due cards (cards ready for review)
2. Apply `new_cards_per_day` limit (default: 20)
3. Apply `max_reviews_per_session` limit (0 = unlimited)
4. Shuffle combined list

### Card Presentation

1. Front side shown (question)
2. User presses Space or clicks to reveal
3. Rating buttons appear

### Rating Submission

1. POST to `/api/review/<id>/` with quality (1-4)
2. SRS algorithm updates scheduling
3. ReviewLog created
4. Streak updated
5. Achievements checked

### Session Completion

1. Stats shown (cards reviewed, time taken)
2. Celebration confetti (if enabled)
3. Options to continue or return

### Review Modes

| Mode | Purpose | Behavior |
|------|---------|----------|
| **Standard** | Normal review | SRS scheduling applied |
| **Struggling** | Cards with EF < 2.0 | 20 card fixed session |
| **Practice** | Early review | No SRS update, streak counts |

Struggling mode is automatically suggested when many cards have low ease factors.

## Deck Import/Export

### Export Format

```json
{
  "name": "Deck Name",
  "description": "Optional description",
  "cards": [
    {
      "card_type": "basic|cloze|reverse|typein",
      "front": "Question or cloze text",
      "back": "Answer",
      "notes": "Optional notes"
    }
  ]
}
```

### Import Process

1. Validate JSON structure
2. Create deck with name/description
3. Create cards in batch
4. Return import summary with success/failure counts

## Theme System

Three-tier theme system:

1. **Database** - User's stored preference
2. **localStorage** - Instant theme toggle
3. **System preference** - `prefers-color-scheme`

### Theme Values

- `light` - Always light mode
- `dark` - Always dark mode
- `system` - Follow OS preference (default)

### Implementation

**Context Processor:**
```python
def user_preferences(request):
    if request.user.is_authenticated:
        preferences, _ = UserPreferences.objects.get_or_create(user=request.user)
        return {'user_theme': preferences.theme}
    return {'user_theme': 'system'}
```

**API Endpoints:**
- `POST /api/theme/` - Sync theme to database
- `GET /api/theme/get/` - Get theme preference

## Email System

### Email Types

| Type | Purpose | Default Frequency |
|------|---------|-------------------|
| verification | Email verification | Once |
| study_reminder | Daily cards due | Daily |
| streak_reminder | Streak at risk | Hourly (noon-10pm) |
| weekly_stats | Weekly summary | Sundays |
| inactivity_nudge | Come back reminder | Daily (inactive 3+ days) |
| achievement | Achievement unlocked | On milestone |

### Branded Email System

Theme-aware emails using user's stored preference:
- Logo inline image
- Light/dark color schemes
- Plain text fallback

### Email Preference Management

- Global unsubscribe via token
- Per-type unsubscribe
- Full preference management without login

### Scheduled Commands

```bash
# Study reminders - every 15 minutes
*/15 * * * * cd /app && uv run python manage.py send_reminders

# Streak reminders - every 2 hours (noon-10pm)
0 12,14,16,18,20,22 * * * cd /app && uv run python manage.py send_streak_reminders

# Weekly stats - Sundays at 9am
0 9 * * 0 cd /app && uv run python manage.py send_weekly_stats

# Inactivity nudges - daily at 10am
0 10 * * * cd /app && uv run python manage.py send_inactivity_nudges
```

## Authentication Flow

### Registration

1. User submits registration form
2. User created as inactive (`is_active=False`)
3. EmailVerificationToken generated
4. Verification email sent
5. Redirect to verification sent page

### Email Verification

1. User clicks verification link
2. Token expiration checked (24 hours)
3. If valid: set `user.is_active=True`, delete token
4. Redirect to login

### Login

1. Django authentication
2. Session created
3. Preferences synced from database
4. Redirect to dashboard

## Achievement System

Achievements are tracked in `cards/achievements.py`. Each achievement has:
- Name and description
- Condition function
- Points value (optional)

### Built-in Achievements

| Achievement | Condition |
|-------------|-----------|
| First Steps | Complete first review |
| Week Warrior | 7-day streak |
| Card Collector | Create 100 cards |
| Review Master | Complete 1000 reviews |
| Perfect Session | 100% accuracy in session |

### Checking Achievements

Achievements are checked after each review:
- Load user's unlocked achievements
- Check each achievement condition
- Send notification email for new unlocks

## API Endpoints

### Review API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/review/<id>/` | POST | Submit card review |
| `/api/practice/<id>/` | POST | Practice review (no SRS) |

### Theme API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/theme/` | POST | Sync theme preference |
| `/api/theme/get/` | GET | Get theme preference |

### Deck API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/deck/<id>/export/` | GET | Export deck as JSON |
| `/deck/<id>/import/` | POST | Import cards from JSON |

## Frontend Architecture

### JavaScript Modules

**app.js**
- Toast notifications (Alpine.js)
- Confetti animations
- Theme toggle
- Mobile navigation

**review.js**
- Card display and rendering
- Keyboard shortcuts
- Cloze rendering
- Type-in validation
- Progress tracking

**dashboard.js**
- Tab-based statistics
- Interactive charts

### Third-Party Libraries

| Library | Purpose | CDN |
|---------|---------|-----|
| TailwindCSS | Utility CSS | jsDelivr |
| Alpine.js | Lightweight reactivity | jsDelivr |
| canvas-confetti | Celebrations | jsDelivr |
| Google Fonts | Typography | Google Fonts |

## Deployment Architecture

### Docker

- **Base Image**: Python 3.11-slim
- **Process Manager**: SupervisorD
- **Scheduler**: Supercronic
- **Web Server**: Gunicorn

### Container Services

1. **Gunicorn** - WSGI server handling Django requests
2. **Supercronic** - Running cron jobs inside container

### Data Persistence

| Mount Point | Purpose |
|-------------|---------|
| `/app/data` | SQLite database |
| `/app/logs` | Application logs |
| `/app/static` | Collected static files |

### Logging

Two log handlers configured:
- `flashcard.log` - General application logs
- `email.log` - Email sending logs

## Performance Considerations

- **Static Files**: WhiteNoise with compression
- **Database**: Indexed foreign keys and timestamps
- **CDN**: External libraries served via CDN
- **Email Deduplication**: EmailLog prevents duplicate sends

## Security Features

- CSRF protection on all forms
- Password hashing via Django auth
- Session-based authentication
- Email unsubscribe tokens (UUID)
- Theme sync API requires authentication

## Extensibility Points

1. **SRS Algorithm**: Pure functions in `srs.py` for easy modification
2. **Email Templates**: HTML and TXT templates in `templates/emails/`
3. **Achievements**: Add new achievements in `achievements.py`
4. **Card Types**: Extend card_type choices in models
5. **Email Types**: Extend email system with new types

## Development Commands

```bash
# Install dependencies
uv sync

# Run development server
uv run python manage.py runserver

# Run migrations
uv run python manage.py migrate

# Create new migrations after model changes
uv run python manage.py makemigrations cards

# Create superuser
uv run python manage.py createsuperuser

# Check for issues
uv run python manage.py check

# Run tests
uv run python manage.py test cards

# Run tests with coverage
uv run coverage run --source='cards' manage.py test cards
uv run coverage report -m

# Send email reminders (run via cron)
uv run python manage.py send_reminders

# Docker deployment
docker compose up -d
docker compose exec web uv run python manage.py migrate
```
