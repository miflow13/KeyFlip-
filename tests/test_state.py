"""Read-only keyboard classification tests using temporary sysfs and udev data."""
from pathlib import Path
import tempfile
import unittest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from keyflip import state


class StateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def make_event(self, name, key_bitmap, properties):
        event = self.root / "input" / name
        (event / "device/capabilities").mkdir(parents=True)
        (event / "device/capabilities/key").write_text(key_bitmap)
        (event / "dev").write_text("13:64")
        udev = self.root / "udev"
        udev.mkdir(exist_ok=True)
        (udev / "c13:64").write_text("".join(f"E:{key}={value}\n" for key, value in properties.items()))
        return event

    def test_external_keyboards_accept_usb_keyboard(self):
        event = self.make_event("event0", "200100050000000", {
            "ID_INPUT_KEYBOARD": "1", "ID_BUS": "usb",
        })
        self.assertEqual(
            state.external_keyboards(self.root / "input", self.root / "udev"),
            [str(event.resolve())],
        )

    def test_external_keyboards_reject_internal_bus(self):
        self.make_event("event0", "200100050000000", {
            "ID_INPUT_KEYBOARD": "1", "ID_BUS": "i8042",
        })
        self.assertEqual(state.external_keyboards(self.root / "input", self.root / "udev"), [])

    def test_internal_state_requires_exactly_one_supported_port(self):
        serio = self.root / "serio"
        (serio / "devices").mkdir(parents=True)
        enabled, error = state.internal_state(serio)
        self.assertIsNone(enabled)
        self.assertIn("No single supported", error)


if __name__ == "__main__":
    unittest.main()
