"""Parser tests.

Fixtures are real (trimmed) logformatter output captured from failed runs of
podman-container-tools/podman, so the parsers are exercised against the exact
shapes CI produces rather than hand-written approximations.
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from selkie.parse import (  # noqa: E402
    Dimensions,
    parse_artifact_name,
    parse_bats,
    parse_ginkgo,
    parse_log,
    strip_html,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8", errors="replace")


class TestArtifactName(unittest.TestCase):
    def test_full_four_axis_name(self):
        d = parse_artifact_name("int-remote-root-fedora-prior.logs")
        self.assertEqual(
            (d.suite, d.mode, d.priv, d.distro),
            ("int", "remote", "root", "fedora-prior"),
        )

    def test_system_suite(self):
        d = parse_artifact_name("sys-local-rootless-debian-sid.logs")
        self.assertEqual(
            (d.suite, d.mode, d.priv, d.distro),
            ("sys", "local", "rootless", "debian-sid"),
        )

    def test_empty_axes_are_preserved(self):
        # build and unit jobs do not vary along mode/priv, so those slots are
        # empty in the artifact name: "build---fedora-current.logs".
        d = parse_artifact_name("build---fedora-current.logs")
        self.assertEqual((d.suite, d.mode, d.priv), ("build", "", ""))
        self.assertEqual(d.distro, "fedora-current")

        u = parse_artifact_name("unit--root-fedora-current.logs")
        self.assertEqual((u.suite, u.mode, u.priv), ("unit", "", "root"))

    def test_label_skips_empty_axes(self):
        self.assertEqual(
            parse_artifact_name("build---fedora-current.logs").label(),
            "build-fedora-current",
        )

    def test_unrecognized_name_does_not_raise(self):
        d = parse_artifact_name("windows-installer-wsl-diag")
        self.assertTrue(d.suite)


class TestStripHtml(unittest.TestCase):
    def test_tags_removed_and_entities_decoded(self):
        self.assertEqual(strip_html("<span class='x'>a &amp; b</span>"), "a & b")


class TestGinkgo(unittest.TestCase):
    def setUp(self):
        self.records = list(parse_ginkgo(strip_html(fixture("ginkgo_failure.html"))))

    def test_finds_the_failure(self):
        self.assertGreaterEqual(len(self.records), 1)

    def test_extracts_test_and_suite_name(self):
        r = self.records[0]
        self.assertEqual(r.test_name, "podman build with a secret from file")
        self.assertEqual(r.suite_name, "Podman build")

    def test_extracts_assertion_message(self):
        r = self.records[0]
        self.assertIn("exit status 125", r.error_excerpt)

    def test_test_file_is_repo_relative(self):
        r = self.records[0]
        self.assertTrue(
            r.test_file.startswith("test/e2e/"),
            f"expected repo-relative path, got {r.test_file!r}",
        )
        # The CI checkout prefix must not survive, or paths differ per runner.
        self.assertNotIn("/var/tmp/", r.test_file)


class TestBats(unittest.TestCase):
    def setUp(self):
        self.records = list(parse_bats(strip_html(fixture("bats_failure.html"))))

    def test_finds_the_failure(self):
        self.assertGreaterEqual(len(self.records), 1)

    def test_extracts_test_name_without_timing(self):
        r = self.records[0]
        self.assertEqual(r.test_name, "podman logs - --until --follow journald")
        # "in 10466ms" is a duration, not part of the test identity.
        self.assertNotIn("10466", r.test_name)

    def test_extracts_failing_assertion(self):
        r = self.records[0]
        self.assertIn("_log_test_follow_until", r.error_excerpt)

    def test_extracts_bats_file(self):
        r = self.records[0]
        self.assertIn("035-logs.bats", r.test_file)


class TestParseLogDispatch(unittest.TestCase):
    def test_int_suite_uses_ginkgo(self):
        recs = parse_log(fixture("ginkgo_failure.html"), Dimensions(suite="int"))
        self.assertGreaterEqual(len(recs), 1)
        self.assertEqual(recs[0].dimensions.suite, "int")

    def test_sys_suite_uses_bats(self):
        recs = parse_log(fixture("bats_failure.html"), Dimensions(suite="sys"))
        self.assertGreaterEqual(len(recs), 1)
        self.assertEqual(recs[0].dimensions.suite, "sys")

    def test_dimensions_are_attached_to_records(self):
        dims = Dimensions("sys", "local", "rootless", "debian-sid")
        recs = parse_log(fixture("bats_failure.html"), dims)
        self.assertEqual(recs[0].dimensions.priv, "rootless")

    def test_clean_log_yields_nothing(self):
        self.assertEqual(parse_log("<html>all passed</html>", Dimensions("int")), [])


if __name__ == "__main__":
    unittest.main()
