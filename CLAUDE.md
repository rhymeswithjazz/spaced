# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference

**Project**: Django flashcard app with SM-2 spaced repetition
**Read first**: [ARCHITECTURE.md](ARCHITECTURE.md) for full technical documentation

## Common Commands

```bash
uv sync                     # Install dependencies
uv run python manage.py runserver    # Start dev server
uv run python manage.py migrate      # Run migrations
uv run python manage.py test cards   # Run tests
uv run python manage.py check        # Check for issues
```

## Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| SRS Algorithm | `cards/srs.py` | Pure functions for SM-2 scheduling |
| Cloze Parser | `cards/cloze.py` | Parse `{{c1::text}}` syntax |
| Models | `cards/models.py` | Deck, Card, ReviewLog, UserPreferences |
| Views | `cards/views/` | Organized by feature (auth, deck, review, etc.) |

## Conventions

- **Pure functions** for business logic (SRS, cloze parsing)
- **Modular views** organized by feature
- **92% test coverage** - write tests for new functionality
- **Dark mode** - all components use `dark:` Tailwind prefixes

## Form Styling

Use `cards/forms.py` `StyledFormMixin` for consistent input styling. Select dropdowns need `appearance-none` with custom chevron.

## Code References

When referencing code, use `file_path:line_number` format.
