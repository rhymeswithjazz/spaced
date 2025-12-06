# Flashcard - Spaced Repetition Learning App

## Project Overview

A self-hosted spaced repetition flashcard application built with Django. Designed for deployment on Synology NAS via Docker/Portainer.

### Key Features
- Create and organize flashcard decks
- Multiple card types (Basic, Cloze deletion, Reverse)
- SM-2 spaced repetition algorithm for optimal review scheduling
- Email verification for new accounts
- Comprehensive email notification system:
  - Study reminders for due cards
  - Streak alerts when streak is at risk
  - Weekly progress reports
  - Inactivity nudges after 3 days
  - Achievement celebrations for milestones
- User email preferences with per-type toggles and global unsubscribe
- Light/dark mode with system preference detection (emails respect user theme)
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
- `pillow` - Image processing for email logo resizing

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
  ├── UserPreferences (theme, cards_per_session, email preferences, streak tracking)
  ├── ReviewReminder (frequency, preferred_time)
  ├── EmailVerificationToken (token, created_at, expires after 24h)
  └── EmailLog (email_type, subject, sent_at - for deduplication)
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
│   ├── models.py            # Deck, Card, ReviewLog, UserPreferences, EmailLog
│   ├── views/               # Views split by feature
│   │   ├── __init__.py      # Exports all views
│   │   ├── auth.py          # Login, Register, logout
│   │   ├── dashboard.py     # Dashboard with statistics
│   │   ├── deck.py          # Deck CRUD, export/import
│   │   ├── card.py          # Card CRUD
│   │   ├── review.py        # Review session, API
│   │   ├── settings.py      # Settings, theme API
│   │   ├── email.py         # Unsubscribe, email preference management
│   │   └── helpers.py       # Shared utilities
│   ├── forms.py             # Django forms with Tailwind styling
│   ├── urls.py              # URL routing
│   ├── srs.py               # SM-2 algorithm (pure functions)
│   ├── cloze.py             # Cloze deletion parsing/rendering (pure functions)
│   ├── email.py             # Email utility module (send_branded_email)
│   ├── achievements.py      # Achievement checking and notifications
│   ├── admin.py             # Admin interface
│   ├── context_processors.py # User theme context
│   ├── tests.py             # Unit tests (177 tests)
│   ├── templates/cards/     # App templates
│   │   └── email/           # Email preference pages
│   └── management/commands/
│       ├── send_reminders.py
│       ├── send_streak_reminders.py
│       ├── send_weekly_stats.py
│       ├── send_inactivity_nudges.py
│       └── send_test_email.py   # For testing email templates
├── templates/
│   ├── base.html            # Base template with nav, theme toggle
│   └── emails/              # Email templates (HTML + plain text)
│       ├── base.html/txt    # Base email template with branding
│       ├── verification.*   # Email verification
│       ├── study_reminder.* # Daily study reminders
│       ├── streak_reminder.* # Streak at risk alerts
│       ├── weekly_stats.*   # Weekly progress report
│       ├── inactivity_nudge.* # Re-engagement emails
│       ├── achievement.*    # Milestone celebrations
│       └── components/      # Reusable email components
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

### Email System

The app includes a comprehensive branded email system with light/dark mode support.

#### Email Types
1. **Study Reminders** - Daily reminders when cards are due
2. **Streak Alerts** - Warns users when their streak is at risk
3. **Weekly Stats** - Sunday progress report with statistics
4. **Inactivity Nudge** - Re-engagement after 3+ days inactive
5. **Achievements** - Celebrates milestones (100 cards, 7/30/100 day streaks)

#### User Preferences
- Per-email-type toggles in Settings page
- Global unsubscribe option
- One-click unsubscribe links in emails (no login required)
- Email preference management page via token URL
- Custom days selection with checkboxes (for custom reminder frequency)

#### Email Branding
- Logo embedded via CID (Content-ID) for reliable display across email clients
- Space Grotesk font with wide letter-spacing matching app header
- Resized to 48x48 using Pillow for optimal display

#### Testing Emails
```bash
# Send test email to a user
uv run python manage.py send_test_email <username> <email_type>

# Available types: study_reminder, streak_reminder, weekly_stats,
#                  inactivity_nudge, achievement, verification

# Force a specific theme
uv run python manage.py send_test_email <username> study_reminder --theme=dark
```

#### Email Preview (Staff Only)
- Visit `/email/preview/<type>/` while logged in as staff
- Add `?theme=dark` for dark mode preview
- Only available when DEBUG=True

#### Cron Schedule (Recommended)
```bash
# Study reminders - hourly check
0 * * * * docker compose exec web uv run python manage.py send_reminders

# Streak reminders - every 2 hours from noon to 10pm
0 12,14,16,18,20,22 * * * docker compose exec web uv run python manage.py send_streak_reminders

# Weekly stats - Sundays at 9am
0 9 * * 0 docker compose exec web uv run python manage.py send_weekly_stats

# Inactivity nudges - daily at 10am
0 10 * * * docker compose exec web uv run python manage.py send_inactivity_nudges
```

## Recent Major Changes

### 2025-12-06 - Comprehensive Email System Overhaul
- **What**: Complete rewrite of email system with branded templates, multiple email types, and user preferences
- **Why**: Previous system was plain text only, limited to study reminders, no user control
- **Impact**: Professional branded emails that respect user theme preference and granular notification controls
- **Features**:
  - **Branded HTML Templates**: All emails use consistent branding with "Spaced" logo, sky blue (#0ea5e9) accent color
  - **Logo Embedding**: CID-embedded logo (48x48, resized from 192x192 via Pillow) for reliable display
  - **Typography**: Space Grotesk font with 0.4em letter-spacing matching app header
  - **Light/Dark Mode**: Emails render in user's preferred theme (SYSTEM defaults to light)
  - **5 Email Types**: Study reminders, streak alerts, weekly stats, inactivity nudges, achievements
  - **User Preferences**: Per-type toggles in Settings, global unsubscribe option
  - **Custom Days Checkboxes**: Reminder schedule uses day name checkboxes instead of number input
  - **One-Click Unsubscribe**: Token-based unsubscribe links work without login
  - **Email Preference Page**: Manage preferences via token URL from any email
  - **Streak Tracking**: UserPreferences now tracks current_streak, longest_streak, last_study_date
  - **Achievement System**: Automatic milestone detection (first review, 100/500/1000 cards, 7/30/100 day streaks)
  - **Deduplication**: EmailLog model prevents duplicate emails same day/week
  - **Testing Tools**: `send_test_email` command and `/email/preview/` endpoint for staff
  - **New Management Commands**: send_streak_reminders, send_weekly_stats, send_inactivity_nudges, send_test_email
- **Migration**: Run `uv run python manage.py migrate` for new email preference fields

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
