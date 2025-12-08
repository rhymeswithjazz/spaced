"""Shared helper functions for views."""

import zoneinfo
from datetime import datetime, time, timedelta, timezone as dt_timezone

from django.utils import timezone

from ..models import UserPreferences


def get_or_create_preferences(user):
    """Get or create user preferences."""
    preferences, _ = UserPreferences.objects.get_or_create(user=user)
    return preferences


def get_user_local_date(user):
    """Get the current date in the user's timezone."""
    preferences = get_or_create_preferences(user)
    user_tz = zoneinfo.ZoneInfo(preferences.user_timezone)
    return timezone.now().astimezone(user_tz).date()


def get_local_day_range(user, date):
    """
    Get the UTC datetime range for a given local date in the user's timezone.

    Returns (start_utc, end_utc) tuple where:
    - start_utc is midnight of the given date in user's timezone, converted to UTC
    - end_utc is midnight of the next day in user's timezone, converted to UTC

    Use with: queryset.filter(reviewed_at__gte=start_utc, reviewed_at__lt=end_utc)
    """
    preferences = get_or_create_preferences(user)
    user_tz = zoneinfo.ZoneInfo(preferences.user_timezone)

    # Create midnight datetime in user's timezone
    local_start = datetime.combine(date, time.min, tzinfo=user_tz)
    local_end = datetime.combine(date + timedelta(days=1), time.min, tzinfo=user_tz)

    # Convert to UTC
    return (local_start.astimezone(dt_timezone.utc), local_end.astimezone(dt_timezone.utc))


def get_local_day_start(user, date):
    """
    Get the UTC datetime for midnight of a given local date in the user's timezone.

    Use with: queryset.filter(reviewed_at__gte=start_utc) for "on or after this date"
    """
    preferences = get_or_create_preferences(user)
    user_tz = zoneinfo.ZoneInfo(preferences.user_timezone)
    local_start = datetime.combine(date, time.min, tzinfo=user_tz)
    return local_start.astimezone(dt_timezone.utc)
