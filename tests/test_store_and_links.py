"""Knowledge base and skip-marker tests."""

import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from selkie import skipmarkers  # noqa: E402
from selkie.fingerprint import fingerprint  # noqa: E402
from selkie.parse import Dimensions, FailureRecord  # noqa: E402
from selkie.store import Store  # noqa: E402


def record(test="podman logs follow", err="assertion failed", run_id=1,
           distro="fedora-prior", priv="root", mode="local", suite="sys",
           created="2026-08-15T10:00:00Z", test_file="test/system/035-logs.bats:399"):
    return FailureRecord(
        test_name=test,
        error_excerpt=err,
        test_file=test_file,
        dimensions=Dimensions(suite, mode, priv, distro),
        run_id=run_id,
        created_at=created,
        run_url=f"https://example.invalid/{run_id}",
    )


class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = Store(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _add(self, rec):
        sig, h = fingerprint(rec)
        return self.store.record(rec, sig, h)

    def test_first_occurrence_creates_pattern(self):
        pattern, is_new = self._add(record())
        self.assertTrue(is_new)
        self.assertEqual(pattern.count, 1)

    def test_same_flake_different_runs_increments_one_pattern(self):
        self._add(record(run_id=1))
        pattern, is_new = self._add(record(run_id=2))
        self.assertFalse(is_new)
        self.assertEqual(pattern.count, 2)
        self.assertEqual(len(self.store.all_patterns()), 1)

    def test_same_run_and_dimensions_is_not_double_counted(self):
        # Re-ingesting a run must be idempotent, otherwise counts inflate every
        # time the tool is re-run over an overlapping window.
        self._add(record(run_id=1))
        pattern, _ = self._add(record(run_id=1))
        self.assertEqual(pattern.count, 1)

    def test_same_run_different_dimensions_counts_separately(self):
        self._add(record(run_id=1, distro="fedora-prior"))
        pattern, _ = self._add(record(run_id=1, distro="debian-sid"))
        self.assertEqual(pattern.count, 2)

    def test_dimension_counts_accumulate(self):
        self._add(record(run_id=1, priv="rootless"))
        self._add(record(run_id=2, priv="rootless"))
        pattern, _ = self._add(record(run_id=3, priv="root"))
        self.assertEqual(pattern.dimensions["priv"], {"rootless": 2, "root": 1})

    def test_first_and_last_seen_track_extremes(self):
        self._add(record(run_id=1, created="2026-08-10T00:00:00Z"))
        pattern, _ = self._add(record(run_id=2, created="2026-08-01T00:00:00Z"))
        self.assertEqual(pattern.first_seen, "2026-08-01T00:00:00Z")
        self.assertEqual(pattern.last_seen, "2026-08-10T00:00:00Z")

    def test_recent_runs_are_capped(self):
        for i in range(1, 16):
            self._add(record(run_id=i))
        pattern = self.store.all_patterns()[0]
        self.assertEqual(pattern.count, 15)
        self.assertLessEqual(len(pattern.recent_runs), Store.MAX_RECENT_RUNS)

    def test_distinct_failures_stay_distinct(self):
        self._add(record(test="podman build", err="exit status 125"))
        self._add(record(test="podman run", err="exit status 125"))
        self.assertEqual(len(self.store.all_patterns()), 2)

    def test_patterns_round_trip_through_disk(self):
        self._add(record())
        reloaded = Store(self.tmp).all_patterns()
        self.assertEqual(len(reloaded), 1)
        self.assertEqual(reloaded[0].tests, ["podman logs follow"])

    def test_runs_scanned_accumulates_across_ingests(self):
        self._add(record())
        self.store.write_index(run_ids=[1, 2, 3])
        index = self.store.write_index(run_ids=[4, 5])
        self.assertEqual(index["runs_scanned"], 5)

    def test_rescanning_the_same_runs_does_not_inflate_coverage(self):
        # Scheduled ingests re-scan overlapping windows, so a run already
        # counted must not be counted again.
        self._add(record())
        self.store.write_index(run_ids=[1, 2, 3])
        index = self.store.write_index(run_ids=[2, 3, 4])
        self.assertEqual(index["runs_scanned"], 4)

    def test_index_separates_runs_from_occurrences(self):
        self._add(record(run_id=1))
        self._add(record(run_id=2))
        index = self.store.write_index(run_ids=[1, 2])
        self.assertEqual(index["total_occurrences"], 2)
        self.assertEqual(index["pattern_count"], 1)


class TestSkipMarkers(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        sys_dir = self.tmp / "test" / "system"
        e2e_dir = self.tmp / "test" / "e2e"
        sys_dir.mkdir(parents=True)
        e2e_dir.mkdir(parents=True)
        (sys_dir / "161-volume-quotas.bats").write_text(
            '@test "quota" {\n'
            '    skip "FIXME #27759: There is a selinux problem with this test"\n'
            "}\n"
        )
        (e2e_dir / "checkpoint_test.go").write_text(
            'func x() {\n'
            '\tSkip("FIXME: #24571 - not working and super flaky")\n'
            "}\n"
        )
        (e2e_dir / "clean_test.go").write_text("func y() {}\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_scan_finds_markers_in_both_languages(self):
        issues = {m.issue for m in skipmarkers.scan(self.tmp)}
        self.assertEqual(issues, {27759, 24571})

    def test_scan_records_file_and_line(self):
        marker = next(m for m in skipmarkers.scan(self.tmp) if m.issue == 27759)
        self.assertTrue(marker.file.endswith("161-volume-quotas.bats"))
        self.assertEqual(marker.line, 2)

    def test_files_without_markers_are_ignored(self):
        files = {m.file for m in skipmarkers.scan(self.tmp)}
        self.assertFalse(any("clean_test.go" in f for f in files))

    def test_link_matches_pattern_to_issue_via_source_file(self):
        store = Store(tempfile.mkdtemp())
        rec = record(test_file="test/system/161-volume-quotas.bats:45")
        sig, h = fingerprint(rec)
        pattern, _ = store.record(rec, sig, h)

        links = skipmarkers.link_patterns([pattern], skipmarkers.scan(self.tmp))
        self.assertEqual(links.get(pattern.signature_hash), [27759])

    def test_unrelated_pattern_is_not_linked(self):
        store = Store(tempfile.mkdtemp())
        rec = record(test_file="test/e2e/build_test.go:116")
        sig, h = fingerprint(rec)
        pattern, _ = store.record(rec, sig, h)

        links = skipmarkers.link_patterns([pattern], skipmarkers.scan(self.tmp))
        self.assertEqual(links, {})

    def test_stale_skips_are_those_without_a_live_pattern(self):
        store = Store(tempfile.mkdtemp())
        rec = record(test_file="test/system/161-volume-quotas.bats:45")
        sig, h = fingerprint(rec)
        pattern, _ = store.record(rec, sig, h)
        pattern.linked_issues = [27759]

        stale = skipmarkers.stale_skips(skipmarkers.scan(self.tmp), [pattern])
        stale_issues = {m.issue for m in stale}
        self.assertNotIn(27759, stale_issues)  # still firing
        self.assertIn(24571, stale_issues)  # not seen in the window


if __name__ == "__main__":
    unittest.main()
