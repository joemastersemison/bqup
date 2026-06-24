from datetime import datetime, timedelta, timezone

import pytest

from bqup.changes import (
    filter_changed,
    is_within_days,
    parse_changed_since,
)


NOW = datetime(2026, 6, 24, 12, 0, 0, tzinfo=timezone.utc)


class _Obj:
    """Minimal stand-in for a Table/Routine that exposes a modified time."""

    def __init__(self, modified):
        self.modified = modified


# ---------------------------------------------------------------------------
# parse_changed_since
# ---------------------------------------------------------------------------

def test_parse_changed_since_none_returns_none():
    assert parse_changed_since(None) is None


def test_parse_changed_since_valid_int_string():
    assert parse_changed_since("7") == 7


def test_parse_changed_since_rejects_non_integer():
    with pytest.raises(ValueError):
        parse_changed_since("seven")


def test_parse_changed_since_rejects_zero_and_negative():
    with pytest.raises(ValueError):
        parse_changed_since("0")
    with pytest.raises(ValueError):
        parse_changed_since("-3")


# ---------------------------------------------------------------------------
# is_within_days
# ---------------------------------------------------------------------------

def test_no_filter_when_days_is_none():
    # When no window is set, everything is in scope (current behavior).
    assert is_within_days(None, None, now=NOW) is True
    assert is_within_days(NOW - timedelta(days=999), None, now=NOW) is True


def test_recent_modification_is_within_window():
    assert is_within_days(NOW - timedelta(days=2), 7, now=NOW) is True


def test_old_modification_is_outside_window():
    assert is_within_days(NOW - timedelta(days=30), 7, now=NOW) is False


def test_boundary_is_inclusive():
    # Modified exactly `days` ago is still considered changed.
    assert is_within_days(NOW - timedelta(days=7), 7, now=NOW) is True


def test_missing_modified_excluded_when_filtering():
    # If we can't tell when it changed, leave it out of a filtered backup.
    assert is_within_days(None, 7, now=NOW) is False


def test_naive_modified_treated_as_utc():
    naive_recent = (NOW - timedelta(days=1)).replace(tzinfo=None)
    assert is_within_days(naive_recent, 7, now=NOW) is True


# ---------------------------------------------------------------------------
# filter_changed
# ---------------------------------------------------------------------------

def test_filter_changed_keeps_all_when_days_none():
    objs = [_Obj(NOW - timedelta(days=500)), _Obj(None)]
    assert filter_changed(objs, None, now=NOW) == objs


def test_filter_changed_keeps_only_recent():
    recent = _Obj(NOW - timedelta(days=1))
    old = _Obj(NOW - timedelta(days=100))
    no_ts = _Obj(None)
    result = filter_changed([recent, old, no_ts], 7, now=NOW)
    assert result == [recent]
