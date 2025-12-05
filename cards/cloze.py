"""
Pure functions for parsing and rendering cloze deletions.

Cloze syntax:
- {{c1::text}} - Simple cloze deletion
- {{c1::text::hint}} - Cloze with hint shown as [hint]

Multiple cloze deletions can exist in a single card.
The number (c1, c2, etc.) groups related deletions.
"""
import re
from dataclasses import dataclass


# Pattern matches {{c1::text}} or {{c1::text::hint}}
CLOZE_PATTERN = re.compile(r'\{\{c(\d+)::([^:}]+)(?:::([^}]+))?\}\}')


@dataclass(frozen=True)
class ClozeMatch:
    """Represents a single cloze deletion found in text."""
    full_match: str
    number: int
    answer: str
    hint: str | None
    start: int
    end: int


def parse_cloze(text: str) -> list[ClozeMatch]:
    """
    Parse all cloze deletions from text.

    Returns a list of ClozeMatch objects sorted by position.
    """
    matches = []
    for match in CLOZE_PATTERN.finditer(text):
        matches.append(ClozeMatch(
            full_match=match.group(0),
            number=int(match.group(1)),
            answer=match.group(2),
            hint=match.group(3),
            start=match.start(),
            end=match.end()
        ))
    return matches


def get_cloze_numbers(text: str) -> set[int]:
    """Get all unique cloze numbers in the text."""
    return {m.number for m in parse_cloze(text)}


def render_cloze_question(text: str, active_number: int | None = None) -> str:
    """
    Render text with cloze deletions as blanks for review.

    If active_number is specified, only that cloze group is blanked.
    If active_number is None, all cloze deletions are blanked.

    Returns text with blanks like [...] or [hint] for active clozes,
    and revealed text for inactive clozes.
    """
    def replace_cloze(match):
        number = int(match.group(1))
        answer = match.group(2)
        hint = match.group(3)

        # If filtering by number and this isn't the active one, show the answer
        if active_number is not None and number != active_number:
            return answer

        # Show blank with optional hint
        if hint:
            return f'[{hint}]'
        return '[...]'

    return CLOZE_PATTERN.sub(replace_cloze, text)


def render_cloze_answer(text: str, active_number: int | None = None) -> str:
    """
    Render text with cloze deletions revealed for the answer side.

    If active_number is specified, highlights that cloze group.
    Otherwise, all answers are shown normally.
    """
    def replace_cloze(match):
        number = int(match.group(1))
        answer = match.group(2)

        # Highlight active cloze, show others normally
        if active_number is not None and number == active_number:
            return f'**{answer}**'
        return answer

    return CLOZE_PATTERN.sub(replace_cloze, text)


def is_valid_cloze(text: str) -> bool:
    """Check if text contains at least one valid cloze deletion."""
    return bool(CLOZE_PATTERN.search(text))


def extract_cloze_answers(text: str) -> list[str]:
    """Extract all cloze answers from text."""
    return [m.answer for m in parse_cloze(text)]


def validate_cloze_syntax(text: str) -> list[str]:
    """
    Validate cloze syntax and return list of error messages.
    Empty list means valid.
    """
    errors = []

    if not is_valid_cloze(text):
        errors.append('No valid cloze deletions found. Use {{c1::text}} syntax.')
        return errors

    # Check for common mistakes

    # Unclosed braces
    open_braces = text.count('{{')
    close_braces = text.count('}}')
    if open_braces != close_braces:
        errors.append('Mismatched braces. Ensure each {{ has a matching }}.')

    # Check for malformed cloze (has {{ but doesn't match pattern)
    potential_cloze = re.findall(r'\{\{[^}]*\}\}', text)
    valid_cloze = CLOZE_PATTERN.findall(text)
    if len(potential_cloze) > len(valid_cloze):
        errors.append('Some cloze deletions are malformed. Use {{c1::text}} or {{c1::text::hint}} format.')

    return errors
