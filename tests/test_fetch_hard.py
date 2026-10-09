"""SSRF guard of fetch_hard.py: the stealth browser must never be pointed at internal targets."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "research-agent", "references"))
import fetch_hard  # noqa: E402


class SsrfGuard(unittest.TestCase):
    def test_rejects_internal_and_non_http_targets(self):
        for url in ["http://127.0.0.1:8080/admin", "http://localhost/", "http://10.0.0.5/",
                    "http://169.254.169.254/latest/meta-data/", "http://[::1]/",
                    "file:///etc/passwd", "ftp://example.com/", "https:///nohost"]:
            with self.subTest(url=url), self.assertRaises(SystemExit):
                fetch_hard.check_url(url)


if __name__ == "__main__":
    unittest.main()
