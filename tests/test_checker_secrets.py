"""A copy is untrusted generated code and must never reach API keys.
python -m unittest tests.test_checker_secrets -v
"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from server import checker

FAKE = "FAKE-SECRET-do-not-leak-123"
ESCAPES = {
    # classic vm escape: a function's .constructor reaches the host realm's Function
    "constructor_escape": 'const p = console.log.constructor("return process")();'
                          'const leak = () => String(p.env.GEMINI_API_KEY);',
    "this_constructor": 'const p = this.constructor.constructor("return process")();'
                        'const leak = () => String(p.env.GEMINI_API_KEY);',
    "direct_process": 'const leak = () => String(process.env.GEMINI_API_KEY);',
    "require_child": 'const leak = () => String(require("child_process").execSync("env"));',
    "import_expr": 'const leak = () => String(import("node:process"));',
}


def copy_source(body):
    return body + (" module.exports = () => ({ press() {}, "
                   "state: () => ({ display: leak(), expression: null, clear_label: null, active_op: null }) });")


class SecretsTest(unittest.TestCase):
    def run_escape(self, body):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "evil.js"
            p.write_text(copy_source(body))
            with mock.patch.dict(os.environ, {"GEMINI_API_KEY": FAKE, "MODEL_API_KEY": FAKE}):
                try:
                    out = json.dumps(checker.check(p, checker.DEFAULT_TRACE))
                except checker.CheckerError as e:
                    out = str(e)
                # also run node directly with the full environment, bypassing the wrapper's env filter
                raw = subprocess.run(["node", str(checker.CHECK_MJS), str(p), str(checker.DEFAULT_TRACE)],
                                     capture_output=True, text=True, timeout=30)
        return out, raw.stdout + raw.stderr

    def test_no_escape_leaks_a_key(self):
        for name, body in ESCAPES.items():
            with self.subTest(name):
                wrapped, raw = self.run_escape(body)
                self.assertNotIn(FAKE, wrapped)
                self.assertNotIn(FAKE, raw)


if __name__ == "__main__":
    unittest.main()
