"""API client tests that need no network."""

import pathlib
import sys
import unittest
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from selkie.github import _StripAuthOnRedirect  # noqa: E402


class _Handler(_StripAuthOnRedirect):
    """Bypass the base class's scheme and loop checks for a unit test."""

    def _redirect(self, url, newurl):
        req = urllib.request.Request(url)
        req.add_header("Authorization", "Bearer secret")
        req.add_header("Accept", "application/json")
        # HTTPRedirectHandler.redirect_request only needs these fields.
        return super().redirect_request(req, None, 302, "Found", {}, newurl)


class TestRedirectAuthStripping(unittest.TestCase):
    """Artifact downloads 302 from api.github.com to blob storage.

    urllib replays every header on the redirected request, and blob storage
    rejects a request carrying a GitHub Authorization header with 401, so the
    credential has to be dropped when the host changes.
    """

    def setUp(self):
        self.h = _Handler()

    def test_authorization_dropped_on_cross_host_redirect(self):
        new = self.h._redirect(
            "https://api.github.com/repos/o/r/actions/artifacts/1/zip",
            "https://productionresultssa0.blob.core.windows.net/actions/x?sig=y",
        )
        self.assertIsNotNone(new)
        self.assertNotIn("Authorization", new.headers)

    def test_other_headers_survive_the_redirect(self):
        new = self.h._redirect(
            "https://api.github.com/x",
            "https://blob.example.invalid/y",
        )
        self.assertIn("Accept", new.headers)

    def test_authorization_kept_on_same_host_redirect(self):
        new = self.h._redirect(
            "https://api.github.com/a",
            "https://api.github.com/b",
        )
        self.assertIn("Authorization", new.headers)


if __name__ == "__main__":
    unittest.main()
