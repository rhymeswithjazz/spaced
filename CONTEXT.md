# Flashcard - Spaced Repetition Learning App

## Project Overview

A self-hosted spaced repetition flashcard application built with Django. Designed for deployment on Synology NAS via Docker/Portainer.

### Key Features
- Create and organize flashcard decks
- Multiple card types (Basic, Cloze deletion, Reverse)
- SM-2 spaced repetition algorithm for optimal review scheduling
- Email verification for new accounts
- Email reminders for due reviews
- Light/dark mode with system preference detection
- SQLite database for simple deployment

## Tech Stack

- **Language**: Python 3.11+
- **Framework**: Django 5.2
- **Database**: SQLite3
- **CSS**: TailwindCSS (via CDN)
- **Package Manager**: uv
- **WSGI Server**: Gunicorn
- **Containerization**: Docker

### Key Libraries
- `django-environ` - Environment variable management
- `gunicorn` - Production WSGI server

## Architecture

### Spaced Repetition Algorithm (SM-2)

The app implements the SM-2 algorithm (`cards/srs.py`):

1. **Quality Ratings (0-5)**: User rates recall difficulty
2. **Ease Factor**: Adjusts based on performance (min 1.3, default 2.5)
3. **Interval Calculation**:
   - First success: 1 day
   - Second success: 6 days
   - Subsequent: interval × ease_factor
4. **Failed reviews**: Reset to 1-day interval

### Data Models

```
Deck (name, description, owner)
  └── Card (front, back, card_type, SRS fields)
       └── ReviewLog (quality, timestamps, before/after states)

User
  ├── UserPreferences (theme, cards_per_session)
  ├── ReviewReminder (frequency, preferred_time)
  └── EmailVerificationToken (token, created_at, expires after 24h)
```

### Card Types
- **Basic**: Standard front/back
- **Cloze**: Fill-in-the-blank using `{{c1::text}}` or `{{c1::text::hint}}` syntax
  - Multiple cloze deletions supported (c1, c2, c3, etc.)
  - Each cloze number becomes a separate review item
  - Parsed and rendered by `cards/cloze.py` (pure functions)
- **Reverse**: Creates both front→back and back→front cards

### Theme System
- Defaults to system preference (prefers-color-scheme)
- User choice saved in both localStorage (instant) and database (sync across devices)
- Syncs from database on login for cross-device consistency

## Project Structure

```
flashcard/
├── config/                  # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── cards/                   # Main application
│   ├── models.py            # Deck, Card, ReviewLog, UserPreferences
│   ├── views/               # Views split by feature
│   │   ├── __init__.py      # Exports all views
│   │   ├── auth.py          # Login, Register, logout
│   │   ├── dashboard.py     # Dashboard with statistics
│   │   ├── deck.py          # Deck CRUD, export/import
│   │   ├── card.py          # Card CRUD
│   │   ├── review.py        # Review session, API
│   │   ├── settings.py      # Settings, theme API
│   │   └── helpers.py       # Shared utilities
│   ├── forms.py             # Django forms with Tailwind styling
│   ├── urls.py              # URL routing
│   ├── srs.py               # SM-2 algorithm (pure functions)
│   ├── cloze.py             # Cloze deletion parsing/rendering (pure functions)
│   ├── admin.py             # Admin interface
│   ├── context_processors.py # User theme context
│   ├── tests.py             # Unit tests (177 tests)
│   ├── templates/cards/     # App templates
│   └── management/commands/
│       └── send_reminders.py
├── templates/
│   └── base.html            # Base template with nav, theme toggle
├── data/                    # SQLite database (Docker volume)
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

## Pages & Features

- **Login/Register**: User authentication with email verification
- **Dashboard**: Overview stats with tabbed statistics panel
  - Progress tab: New/Learning/Mature cards, retention rate, struggling cards
  - Activity tab: Reviews today/week/month, current and best streaks
  - Forecast tab: 7-day calendar of upcoming reviews
  - By Deck tab: Per-deck statistics table
- **Decks**: List, create, edit, delete, import decks
- **Deck Detail**: View cards, due count, export deck, reset deck, quick actions
- **Card CRUD**: Add/edit/delete cards with type selection and cloze validation
- **Review Session**: Interactive card review with keyboard shortcuts, shuffled order
- **Settings**: Theme, cards per session, email reminder preferences
- **Export/Import**: JSON format for deck sharing and backup

## Development

### Local Setup

```bash
# Install dependencies
uv sync

# Apply migrations
uv run python manage.py migrate

# Create superuser
uv run python manage.py createsuperuser

# Run development server
uv run python manage.py runserver
```

### Environment Variables

Copy `.env.example` to `.env` and configure:
- `SECRET_KEY`: Django secret key (required in production)
- `DEBUG`: Set to False in production
- `ALLOWED_HOSTS`: Comma-separated hostnames
- `EMAIL_*`: SMTP settings for reminders

## Deployment (Synology NAS / Portainer)

### Option 1: Docker Compose

```bash
# Build and start
docker compose up -d

# Apply migrations
docker compose exec web uv run python manage.py migrate

# Create admin user
docker compose exec web uv run python manage.py createsuperuser
```

### Option 2: Portainer Stack

1. Create new stack in Portainer
2. Paste `docker-compose.yml` content
3. Set environment variables in Portainer UI
4. Deploy stack

### Email Reminders

Set up a cron job or scheduled task to run:
```bash
docker compose exec web uv run python manage.py send_reminders
```

Recommended: Daily at user's preferred reminder time.

## Recent Major Changes

### 2025-12-06 - Deck Reset & Due/New Card Separation
- **What**: Added deck reset functionality and fixed how new vs due cards are counted
- **Why**: New cards were incorrectly showing as "due", causing confusion. Users needed ability to reset deck progress.
- **Impact**: Dashboard now correctly distinguishes between cards due for review and new cards never studied
- **Features**:
  - **Due vs New separation**: `cards_due_count()` now excludes new cards (repetitions=0)
  - Added `cards_new_count()` method to Deck model
  - Dashboard shows "X due" (yellow) or "X new" (blue) badges on deck cards
  - Review session prioritizes due cards over new cards (due cards studied first)
  - **Deck Reset**: Reset button on deck detail page with confirmation modal
  - Confirmation requires typing deck name to prevent accidental resets
  - Reset clears all progress: ease_factor=2.5, interval=0, repetitions=0
  - Reset also deletes all review history for the deck
  - Dashboard deck cards now use flexbox for consistent footer alignment
  - Play icon replaced with "Review" button on deck cards

### 2025-12-05 - Email Verification for New Accounts
- **What**: Added email verification requirement for new user registrations
- **Why**: Ensure users provide valid email addresses before activating accounts
- **Impact**: New accounts are created with `is_active=False` until email is verified
- **Features**:
  - EmailVerificationToken model with 24-hour expiration
  - Verification email sent on registration with unique token link
  - Verification success activates account and redirects to login
  - Expired token page with option to request new link
  - Resend verification email page (doesn't reveal account existence)
  - 14 new tests covering all verification flows

### 2025-12-05 - Views Refactoring & Comprehensive Test Suite
- **What**: Split monolithic views.py into feature modules, added comprehensive test suite
- **Why**: Improve maintainability and ensure code quality
- **Impact**: Easier to navigate codebase, safer refactoring with test safety net
- **Changes**:
  - Split 624-line `views.py` into 7 focused modules under `cards/views/`
  - Added comprehensive unit tests for SRS algorithm, cloze parsing, models, forms, and views
  - All pure functional modules (srs.py, cloze.py) at 92-98% coverage
  - All forms at 100% coverage
  - View integration tests for all CRUD operations and API endpoints

### 2025-12-05 - Cloze Cards, Statistics Dashboard, Export/Import
- **What**: Implemented cloze card rendering, comprehensive dashboard statistics, deck export/import
- **Why**: Enable advanced card types and provide learning insights
- **Impact**: Users can create cloze deletion cards, track detailed progress, and share decks
- **Features**:
  - Cloze card parsing with `{{c1::text}}` and `{{c1::text::hint}}` syntax
  - Cloze cards expand into multiple review items (one per cloze number)
  - Dashboard statistics with 4 tabs (Progress, Activity, Forecast, By Deck)
  - Retention rate, streak tracking, card maturity classification
  - JSON export/import for deck backup and sharing
  - Review cards are now shuffled for better learning
  - Form validation for cloze syntax

### 2025-12-05 - Complete UI Implementation
- **What**: Full web UI with TailwindCSS, dark/light mode
- **Why**: Provide usable interface for flashcard management and review
- **Impact**: App is now functional end-to-end
- **Features**:
  - Authentication (login/register/logout)
  - Dashboard with stats and deck overview
  - Deck and card CRUD operations
  - Interactive review session with keyboard shortcuts
  - Theme toggle with localStorage + database sync
  - Settings page for preferences and reminders

### 2025-12-04 - Initial Bootstrap
- **What**: Project initialization with Django, Docker, and SM-2 algorithm
- **Why**: Create foundation for spaced repetition flashcard app
- **Impact**: Basic models and infrastructure ready for UI development

## TODO - Test Coverage Improvements

The following areas have lower test coverage and should be addressed:

### High Priority
- [ ] **Deck Import (cards/views/deck.py:125-189)** - 64% coverage
  - Add tests for file upload handling
  - Test JSON parsing error cases
  - Test duplicate deck name handling
  - Test invalid card type handling

### Medium Priority
- [ ] **Dashboard streak calculation (cards/views/dashboard.py:68, 78-86)** - 87% coverage
  - Test streak calculation with gaps
  - Test longest streak edge cases
  - Test empty review history

### Low Priority
- [ ] **Send Reminders Command (cards/management/commands/send_reminders.py)** - 0% coverage
  - Requires mocking email sending
  - Test frequency logic (daily, weekly, custom)
  - Test preferred time matching
  - Consider if worth the complexity

### Running Tests
```bash
# Run all tests
uv run python manage.py test cards

# Run with coverage report
uv run coverage run --source='cards' manage.py test cards
uv run coverage report -m

# Run specific test class
uv run python manage.py test cards.tests.CardFormTests
```
