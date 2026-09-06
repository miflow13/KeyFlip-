"""Exercise the tray's Python entry point with real Gio argument parsing.

Use Gio.Application in place of GTK so no display or keyboard hardware is needed.
"""
import ast
import os
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROBE = r'''
import ast
from pathlib import Path
import runpy
import sys
import types
from gi.repository import Gio, GLib

root = Path.cwd()
source = ast.parse((root / "src/keyflip/application.py").read_text())
handler = next(node for node in source.body
               if isinstance(node, ast.FunctionDef) and node.name == "on_command_line")
namespace = {
    "request_quit": lambda app: print("QUIT", flush=True),
    "on_activate": lambda app: (print("OPEN", flush=True) or
        types.SimpleNamespace(show_preferences=lambda: print("PREFERENCES", flush=True))),
    "get_keyboard_window": lambda app, present=False: (
        print("OPEN" if present else "CREATE", flush=True) or
        types.SimpleNamespace(show_preferences=lambda: print("PREFERENCES", flush=True))
    ),
}
exec(compile(ast.Module(body=[handler], type_ignores=[]), "application.py", "exec"), namespace)
app = Gio.Application(application_id="io.github.miflow13.KeyFlip.Test",
                      flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE |
                            Gio.ApplicationFlags.NON_UNIQUE)
app.get_windows = lambda: []
for option in ("quit", "preferences"):
    app.add_main_option(option, 0, GLib.OptionFlags.NONE, GLib.OptionArg.NONE, option, None)
app.connect("command-line", namespace["on_command_line"])
sys.modules["keyflip.application"] = types.SimpleNamespace(run=lambda argv: app.run(argv))
sys.argv = [str(root / "app.py"), *sys.argv[1:]]
runpy.run_path(str(root / "app.py"), run_name="__main__")
'''


class CommandLineTests(unittest.TestCase):
    def run_entrypoint(self, *args):
        result = subprocess.run(
            ["/usr/bin/python3", "-c", PROBE, *args], cwd=ROOT,
            env={**os.environ, "GSETTINGS_BACKEND": "memory"},
            capture_output=True, text=True, timeout=10,
        )
        return result

    def test_tray_quit_does_not_open_window(self):
        result = self.run_entrypoint("--quit")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "QUIT")

    def test_preferences_reaches_handler(self):
        result = self.run_entrypoint("--preferences")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "CREATE\nPREFERENCES")

    def test_normal_launch_opens_window(self):
        result = self.run_entrypoint()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "OPEN")

    def test_invalid_option_returns_failure(self):
        result = self.run_entrypoint("--not-a-keyflip-option")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("OPEN", result.stdout)

    def test_preferences_header_uses_themed_app_header(self):
        source = ast.parse((ROOT / "src/keyflip/window.py").read_text())
        preferences = next(
            node for node in source.body
            if isinstance(node, ast.ClassDef) and node.name == "PreferencesWindow"
        )
        init = next(
            node for node in preferences.body
            if isinstance(node, ast.FunctionDef) and node.name == "__init__"
        )
        themed_headers = [
            call for call in ast.walk(init)
            if isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "add_css_class"
            and any(isinstance(arg, ast.Constant) and arg.value == "app-header" for arg in call.args)
        ]
        self.assertTrue(themed_headers, "Preferences header must follow the app's light/dark styling")

    def test_automatic_switches_use_contrasting_theme_style(self):
        source = (ROOT / "src/keyflip/window.py").read_text()
        self.assertGreaterEqual(source.count('add_css_class("automatic-switch")'), 2)
        self.assertIn("switch.automatic-switch:checked", source)
        self.assertIn("switch.automatic-switch slider", source)
