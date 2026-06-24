"""Integration-ish tests for threading the changed-since window through
Dataset / Table construction and export, using lightweight fakes instead of
a real BigQuery client.
"""
import os
from datetime import datetime, timedelta, timezone

from bqup.dataset import Dataset

NOW = datetime(2026, 6, 24, 12, 0, 0, tzinfo=timezone.utc)


class FakeFullTable:
    def __init__(self, modified, view_query='', mview_query='', schema=None):
        self.modified = modified
        self.view_query = view_query
        self.mview_query = mview_query
        self.schema = schema or []


class FakeBQTable:
    """Stand-in for bigquery.table.TableListItem."""

    def __init__(self, table_id, table_type):
        self.table_id = table_id
        self.table_type = table_type
        self.reference = ("ref", table_id)


class FakeBQDataset:
    def __init__(self, dataset_id):
        self.dataset_id = dataset_id
        self.reference = ("dsref", dataset_id)


class FakeClient:
    """Implements just the surface Dataset/Table touch."""

    def __init__(self, list_items, full_tables):
        self.project = "fake-project"
        self._list_items = list_items
        self._full_tables = full_tables

    def list_tables(self, ref):
        return self._list_items

    def get_table(self, ref, retry=None, timeout=None):
        return self._full_tables[ref[1]]


class FakeProject:
    def __init__(self, client):
        self.client = client
        self.datasets = []


def _build_dataset(list_items, full_tables, changed_since_days):
    client = FakeClient(list_items, full_tables)
    project = FakeProject(client)
    bq_dataset = FakeBQDataset("ds1")
    return Dataset(project, False, False, bq_dataset, changed_since_days, now=NOW)


def test_table_captures_modified_timestamp():
    items = [FakeBQTable("v1", "VIEW")]
    full = {"v1": FakeFullTable(NOW - timedelta(days=1), view_query="SELECT 1")}
    ds = _build_dataset(items, full, changed_since_days=None)
    assert ds.tables[0].modified == NOW - timedelta(days=1)


def test_plain_table_is_fetched_for_modified_when_filtering():
    # A plain TABLE without --schema would normally not be fetched; the
    # changed-since window must still learn its modified time.
    items = [FakeBQTable("t1", "TABLE")]
    full = {"t1": FakeFullTable(NOW - timedelta(days=2))}
    ds = _build_dataset(items, full, changed_since_days=7)
    assert ds.tables[0].modified == NOW - timedelta(days=2)


def test_dataset_drops_objects_outside_window():
    items = [FakeBQTable("recent", "VIEW"), FakeBQTable("stale", "VIEW")]
    full = {
        "recent": FakeFullTable(NOW - timedelta(days=1), view_query="SELECT 1"),
        "stale": FakeFullTable(NOW - timedelta(days=100), view_query="SELECT 2"),
    }
    ds = _build_dataset(items, full, changed_since_days=7)
    assert [t.table_id for t in ds.tables] == ["recent"]


def test_summary_reports_kept_and_skipped(capsys):
    items = [FakeBQTable("recent", "VIEW"), FakeBQTable("stale", "VIEW")]
    full = {
        "recent": FakeFullTable(NOW - timedelta(days=1), view_query="SELECT 1"),
        "stale": FakeFullTable(NOW - timedelta(days=100), view_query="SELECT 2"),
    }
    _build_dataset(items, full, changed_since_days=7)
    out = capsys.readouterr().out
    assert "Kept 1 of 2 object(s) modified in the last 7 day(s) (skipped 1 unchanged)." in out


def test_no_summary_when_not_filtering(capsys):
    items = [FakeBQTable("v1", "VIEW")]
    full = {"v1": FakeFullTable(NOW - timedelta(days=1), view_query="SELECT 1")}
    _build_dataset(items, full, changed_since_days=None)
    out = capsys.readouterr().out
    assert "Kept" not in out


def test_export_skips_dataset_with_no_changed_objects(tmp_path):
    items = [FakeBQTable("stale", "VIEW")]
    full = {"stale": FakeFullTable(NOW - timedelta(days=100), view_query="SELECT 2")}
    ds = _build_dataset(items, full, changed_since_days=7)

    project_dir = str(tmp_path)
    ds.export(project_dir)

    assert not os.path.exists(os.path.join(project_dir, "ds1"))
