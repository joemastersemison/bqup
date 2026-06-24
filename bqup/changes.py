"""Helpers for restricting a backup to recently changed objects.

This module is deliberately free of any BigQuery imports so the filtering
logic can be unit tested without a client or network access.
"""
from datetime import datetime, timedelta, timezone


def parse_changed_since(value):
    """Parse the ``--changed-since`` CLI value into a positive day count.

    Parameters
    ----------
    value : str or None
        The raw value from the command line. ``None`` means no filtering.

    Returns
    -------
    int or None
        ``None`` if no window was requested, otherwise the number of days.

    Raises
    ------
    ValueError
        If the value is not a positive integer.
    """
    if value is None:
        return None
    days = int(value)  # raises ValueError on non-integer input
    if days <= 0:
        raise ValueError(f"--changed-since must be a positive number of days, got {days}")
    return days


def is_within_days(modified, days, now=None):
    """Return whether ``modified`` falls within the past ``days`` days.

    Parameters
    ----------
    modified : datetime or None
        The object's last-modified time. May be timezone-aware or naive
        (naive values are assumed to be UTC). ``None`` means the time is
        unknown.
    days : int or None
        The size of the window in days. ``None`` disables filtering, so
        everything is considered in scope.
    now : datetime, optional
        Reference point for "now"; defaults to the current UTC time.

    Returns
    -------
    bool
    """
    if days is None:
        return True
    if modified is None:
        return False

    if now is None:
        now = datetime.now(timezone.utc)

    modified = _as_utc(modified)
    now = _as_utc(now)

    cutoff = now - timedelta(days=days)
    return modified >= cutoff


def filter_changed(objects, days, now=None):
    """Filter objects exposing a ``modified`` attribute by the day window.

    Parameters
    ----------
    objects : iterable
        Items with a ``modified`` datetime attribute (e.g. Table, Routine).
    days : int or None
        Window size; ``None`` keeps every object.
    now : datetime, optional
        Reference point for "now".

    Returns
    -------
    list
        The objects whose ``modified`` time is within the window.
    """
    if days is None:
        return list(objects)
    return [o for o in objects if is_within_days(getattr(o, 'modified', None), days, now=now)]


def _as_utc(value):
    """Return ``value`` as a timezone-aware UTC datetime (assume UTC if naive)."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
