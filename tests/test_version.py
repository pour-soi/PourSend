import unittest

from core.version import __version__


class VersionTests(unittest.TestCase):
    def test_application_version_is_release_version(self):
        self.assertEqual(__version__, "2.1.2")


if __name__ == "__main__":
    unittest.main()
