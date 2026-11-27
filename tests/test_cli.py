import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from hookroute.cli import main


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_EVENT = (ROOT / "examples/event.json").read_text(encoding="utf-8")
MATCH = {"rule": "demo-pr", "would_send": True, "reason": "rule_matched", "sent": False}
NO_MATCH = {"rule": None, "would_send": False, "reason": "no_rule_matched", "sent": False}


class CLITests(unittest.TestCase):
    def invoke(self, argv, stdin=PUBLIC_EVENT):
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            patch("sys.stdin", io.StringIO(stdin)),
            patch("socket.socket", side_effect=AssertionError("socket creation attempted")),
            patch("socket.create_connection", side_effect=AssertionError("connection attempted")),
            patch("socket.getaddrinfo", side_effect=AssertionError("DNS lookup attempted")),
            patch("subprocess.Popen", side_effect=AssertionError("subprocess attempted")),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            status = main(argv)
        return status, stdout.getvalue(), stderr.getvalue()

    def test_stdin_with_network_tripwire_in_both_modes(self):
        for flags in ([], ["--dry-run"]):
            with self.subTest(flags=flags):
                status, out, err = self.invoke(["event", *flags])
                self.assertEqual((status, json.loads(out), err), (0, MATCH, ""))

    def test_file_and_custom_routes(self):
        status, out, err = self.invoke([
            "event", "--dry-run", "--routes", str(ROOT / "routes.toml"),
            "--file", str(ROOT / "examples/no-match.json"),
        ], stdin="ignored")
        self.assertEqual((status, json.loads(out), err), (0, NO_MATCH, ""))

    def test_errors_do_not_echo_input(self):
        marker = "untrusted-example-marker"
        cases = [
            ([marker], PUBLIC_EVENT, "invalid arguments; see hookroute --help"),
            (["event", f"--{marker}"], PUBLIC_EVENT, "invalid arguments; see hookroute --help"),
            (["event", "--file"], PUBLIC_EVENT, "invalid arguments; see hookroute --help"),
            (["event", "--file", marker], PUBLIC_EVENT, "could not read event"),
            (["event", "--routes", marker], PUBLIC_EVENT, "could not read routes"),
            (["event"], "not JSON " + marker, "invalid JSON event"),
            (["event"], json.dumps(json.loads(PUBLIC_EVENT) | {"state": marker}), "invalid event state"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "routes.toml"
            route_text = (ROOT / "routes.toml").read_text(encoding="utf-8")
            for text, message in [
                ('routes = ["' + marker, "invalid routes TOML"),
                (route_text.replace('"demo-pr"', f'"{marker} just a label"'), "invalid route name"),
                (route_text.replace('"done"', f'"{marker}"'), "invalid route states"),
                (route_text.replace("/hook", f"/hook?{marker}"), "route url must be HTTP(S) without credentials, query or fragment"),
            ]:
                file.write_text(text, encoding="utf-8")
                status, out, err = self.invoke(["event", "--routes", str(file)])
                self.assertEqual((status, out, json.loads(err)), (2, "", {"error": message}))
                self.assertNotIn(marker, err)
        for args, payload, message in cases:
            with self.subTest(args=args, message=message):
                status, out, err = self.invoke(args, payload)
                self.assertEqual((status, out, json.loads(err)), (2, "", {"error": message}))
                self.assertNotIn(marker, err)

    def test_does_not_open_secret_files(self):
        for path in (".env.example", "auth.json", "service.json", "/home/user/.ssh/config"):
            with self.subTest(path=path), patch("pathlib.Path.read_text") as read:
                status, out, err = self.invoke(["event", "--routes", path])
                read.assert_not_called()
                self.assertEqual((status, out, json.loads(err)), (2, "", {"error": "could not read routes"}))

    def test_real_entry_points(self):
        for command in ([str(ROOT / "bin/hookroute")], [sys.executable, "-m", "hookroute"]):
            with self.subTest(command=command):
                result = subprocess.run(
                    [*command, "event", "--dry-run"], input=PUBLIC_EVENT, text=True,
                    capture_output=True, cwd=ROOT, check=False,
                )
                self.assertEqual((result.returncode, json.loads(result.stdout), result.stderr),
                                 (0, MATCH, ""))
