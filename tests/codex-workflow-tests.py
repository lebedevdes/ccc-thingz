"""Run the copy skills' inline Bash against fake clipboard tools."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")
RM = shutil.which("rm")
SKILLS = ("txt-copy", "md-copy")
FAKE = '''
import os
from pathlib import Path
import sys
Path(os.environ["CLIPBOARD_CAPTURE"]).write_bytes(sys.stdin.buffer.read())
Path(os.environ["CLIPBOARD_BACKEND"]).write_text(Path(sys.argv[0]).name + " " + " ".join(sys.argv[1:]))
'''


class InlineCopyTests(unittest.TestCase):
    def run_copy(self, skill, tools, platform="linux-gnu"):
        source = (ROOT / f"codex_plugins/workflow/skills/{skill}/SKILL.md").read_text()
        snippets = re.findall(r"```bash\n(.*?)\n```", source, re.S)
        self.assertEqual(len(snippets), 2)
        # Run the documented backend selection and cleanup, without touching the
        # real clipboard. The first snippet's selected text is supplied as bytes.
        with tempfile.TemporaryDirectory(prefix="workflow copy ") as directory:
            root = Path(directory)
            bin_dir = root / "fake tools"
            bin_dir.mkdir()
            (bin_dir / "rm").symlink_to(RM)
            for name in tools:
                tool = bin_dir / name
                tool.write_text(f"#!{sys.executable}\n" + FAKE)
                tool.chmod(0o755)
            selected = root / "selected text"
            payload = "Привет 👋\r\n\t`literal` $(touch SHOULD_NOT_EXIST) $value\n  indented\n".encode()
            selected.write_bytes(payload)
            capture, backend = root / "captured bytes", root / "backend"
            env = {**os.environ, "PATH": str(bin_dir), "tmpfile": str(selected),
                   "CLIPBOARD_CAPTURE": str(capture), "CLIPBOARD_BACKEND": str(backend),
                   "CLIPBOARD_TEST_PLATFORM": platform}
            result = subprocess.run(
                [BASH, "-c", 'OSTYPE="$CLIPBOARD_TEST_PLATFORM"\n' + snippets[1]],
                env=env, cwd=root, capture_output=True,
            )
            self.assertFalse(selected.exists(), "temporary selection must be removed")
            self.assertFalse((root / "SHOULD_NOT_EXIST").exists())
            if tools:
                self.assertEqual(capture.read_bytes(), payload)
            return result, backend.read_text() if backend.exists() else None

    def test_macos_uses_pbcopy(self):
        for skill in SKILLS:
            with self.subTest(skill=skill):
                result, backend = self.run_copy(skill, ("pbcopy", "xclip"), "darwin")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(backend, "pbcopy ")

    def test_xclip_uses_clipboard_selection(self):
        for skill in SKILLS:
            with self.subTest(skill=skill):
                result, backend = self.run_copy(skill, ("xclip", "xsel"))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(backend, "xclip -selection clipboard")

    def test_xsel_fallback(self):
        for skill in SKILLS:
            with self.subTest(skill=skill):
                result, backend = self.run_copy(skill, ("xsel",))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(backend, "xsel --clipboard --input")

if __name__ == "__main__":
    unittest.main(verbosity=2)
