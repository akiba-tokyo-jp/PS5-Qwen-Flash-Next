# SPDX-License-Identifier: MIT
"""Enforce the current owner-requested development restriction before console I/O."""
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("console_tool", ROOT / "tools/console.py")
console = importlib.util.module_from_spec(spec)
spec.loader.exec_module(console)


class DevelopmentRestriction(unittest.TestCase):
    def test_console_commands_are_blocked_before_network_builds_or_local_writes(self):
        for command in ("inspect", "close"):
            argv = ["console.py", command, "--host", "example.invalid", "--workspace", str(ROOT),
                    "--out", str(ROOT / "never-created-by-policy-test")]
            with self.subTest(command=command), patch.object(sys, "argv", argv), \
                 patch.object(console.urllib.request, "build_opener") as network, \
                 patch.object(console.subprocess, "run") as build, \
                 patch.object(Path, "mkdir") as mkdir, contextlib.redirect_stderr(io.StringIO()), \
                 self.assertRaises(SystemExit) as error:
                console.main()
            self.assertEqual(error.exception.code, 2)
            network.assert_not_called()
            build.assert_not_called()
            mkdir.assert_not_called()


if __name__ == "__main__":
    unittest.main()
