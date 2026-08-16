"""Fingerprint tests.

The property that matters: two occurrences of the same flake must produce the
same hash despite differing timestamps, container IDs, durations and temp
paths, while genuinely different failures must not collide.
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from selkie.fingerprint import normalize, signature, signature_hash  # noqa: E402


class TestNormalize(unittest.TestCase):
    def test_strips_timestamps(self):
        a = normalize("failed at 08/15/26 20:38:15.857")
        b = normalize("failed at 08/16/26 02:11:09.001")
        self.assertEqual(a, b)

    def test_strips_iso_timestamps(self):
        a = normalize("since 2026-08-14T12:19:41Z")
        b = normalize("since 2026-08-15T22:04:03Z")
        self.assertEqual(a, b)

    def test_strips_durations(self):
        a = normalize("podman logs test in 10466ms")
        b = normalize("podman logs test in 92ms")
        self.assertEqual(a, b)

    def test_strips_container_ids(self):
        a = normalize("started 8cd354e7f35ffedbac06486c97a0ca3c65489cf7bd1afc9a8c5a8e8fcaa630df")
        b = normalize("started 1129f00d2b21f0e04d9dcbec0a91b0c1e3b16c39e83a2e5d0e7f9a3c5b4d6e8f")
        self.assertEqual(a, b)

    def test_strips_random_test_resource_names(self):
        # Podman's test helpers append a random suffix to every container name.
        a = normalize("podman logs c-ltfu-t93-uxvehj2c")
        b = normalize("podman logs c-ltfu-t93-qq81zzk4")
        self.assertEqual(a, b)

    def test_strips_go_stack_addresses(self):
        a = normalize("PodmanExitCleanly(0xc0004c5600) +0x114")
        b = normalize("PodmanExitCleanly(0xc000911800) +0x9b")
        self.assertEqual(a, b)

    def test_strips_ci_checkout_prefix(self):
        # Different runners check out under different parent directories.
        a = normalize("/var/tmp/podman-container-tools/podman/test/e2e/build_test.go")
        b = normalize("/var/tmp/other-org/podman/test/e2e/build_test.go")
        self.assertEqual(a, b)

    def test_strips_bats_scratch_dirs(self):
        a = normalize("/tmp/CI_plDj/podman_bats.clENUg/file")
        b = normalize("/tmp/CI_9xQm/podman_bats.aB3dEf/file")
        self.assertEqual(a, b)

    def test_strips_ports(self):
        a = normalize("bind: 0.0.0.0:43185 address already in use")
        b = normalize("bind: 0.0.0.0:42611 address already in use")
        self.assertEqual(a, b)

    def test_preserves_the_meaningful_message(self):
        out = normalize("Command failed with exit status 125. See above.")
        self.assertIn("Command failed with exit status", out)


class TestSignature(unittest.TestCase):
    def test_same_flake_two_runs_collapses(self):
        run_a = signature(
            "podman logs - --until --follow journald",
            "`_log_test_follow_until journald' failed at 08/15/26 20:38:15.857 "
            "in 10466ms for c-ltfu-t93-uxvehj2c",
        )
        run_b = signature(
            "podman logs - --until --follow journald",
            "`_log_test_follow_until journald' failed at 08/16/26 03:02:11.004 "
            "in 9871ms for c-ltfu-t93-pp42aakz",
        )
        self.assertEqual(run_a, run_b)
        self.assertEqual(signature_hash(run_a), signature_hash(run_b))

    def test_different_tests_do_not_collide(self):
        # A generic message is common across unrelated tests, so the test
        # identity has to be part of the signature.
        a = signature("podman build with a secret", "Command failed with exit status 125.")
        b = signature("podman run with a volume", "Command failed with exit status 125.")
        self.assertNotEqual(signature_hash(a), signature_hash(b))

    def test_different_errors_do_not_collide(self):
        a = signature("podman build", "Command failed with exit status 125.")
        b = signature("podman build", "timed out waiting for container to start")
        self.assertNotEqual(signature_hash(a), signature_hash(b))

    def test_hash_is_stable_and_short(self):
        h = signature_hash(signature("t", "e"))
        self.assertEqual(len(h), 16)
        self.assertEqual(h, signature_hash(signature("t", "e")))


if __name__ == "__main__":
    unittest.main()
