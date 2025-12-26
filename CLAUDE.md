# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Architecture

Read ARCHITECTURE.md to get an understanding of the project's architecture.

## Commands

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

## Architecture

Django flashcard app with SM-2 spaced repetition algorithm for optimal review scheduling.

### Key Components

- **`cards/srs.py`**: Pure functional implementation of SM-2 algorithm. Quality ratings 0-5, ease factor adjustments, interval calculations. Used by `Card.review()` method.

- **`cards/cloze.py`**: Pure functions for parsing and rendering cloze deletions. Handles `{{c1::text}}` and `{{c1::text::hint}}` syntax.

- **`cards/models.py`**: Core models - `Deck`, `Card` (with SRS fields), `ReviewLog`, `UserPreferences`, `ReviewReminder`. Cards belong to Decks, which belong to Users.

- **`cards/views/`**: Views split by feature - `auth.py` (login/register), `dashboard.py`, `deck.py` (CRUD + export/import), `card.py` (CRUD), `review.py` (session + API), `settings.py` (preferences + theme API).

- **`templates/base.html`**: Base template with TailwindCSS (CDN), theme toggle, navigation. Theme syncs between localStorage and database via context processor.

- **`cards/context_processors.py`**: Injects `user_theme` into all templates for theme persistence.

### Review Session Flow

1. User starts review → `review_session` view fetches due cards as JSON
2. JavaScript handles card display and keyboard shortcuts (Space, 1-4)
3. Rating submitted via POST to `/api/review/<id>/`
4. `Card.review()` calls `srs.calculate_review()` and updates scheduling

### Theme System

- Defaults to system preference (`prefers-color-scheme`)
- Toggle saves to localStorage (instant) + database via API (persistence)
- On login, database preference syncs to localStorage

### Cloze Card Syntax

```
{{c1::answer}}           - Simple cloze deletion
{{c1::answer::hint}}     - Cloze with hint shown as placeholder
{{c1::word1}} and {{c2::word2}}  - Multiple deletions (each becomes separate review)
```

### UI Styling Conventions

- **Form inputs**: Use consistent styling defined in `cards/forms.py` `StyledFormMixin`
- **Select dropdowns**: Use `appearance-none` with custom SVG chevron for cross-browser consistency. Copy styling from `StyledFormMixin` for select elements.
- **Color scheme**: Primary (blue), success (green), warning (yellow), danger (red)
- **Dark mode**: All components must support dark mode via `dark:` Tailwind prefixes

### Deck Export/Import Format

```json
{
  "name": "Deck Name",
  "description": "Optional description",
  "cards": [
    {
      "card_type": "basic|cloze|reverse",
      "front": "Question or cloze text",
      "back": "Answer",
      "notes": "Optional notes"
    }
  ]
}
```
