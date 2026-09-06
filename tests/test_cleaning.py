"""Exercise filtering and recovery without grabbing the user's input devices."""
from pathlib import Path
import errno
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from keyflip.cleaning import CleaningSession

CODES = SimpleNamespace(
    EV_SYN=0, EV_KEY=1, EV_REL=2, EV_ABS=3, EV_MSC=4,
    MSC_SCAN=4, SYN_DROPPED=3,
    KEY={1: 'KEY_ESC', 30: 'KEY_A', 115: 'KEY_VOLUMEUP', 464: 'KEY_FN'},
    BTN={272: 'BTN_LEFT', 273: 'BTN_RIGHT', 330: 'BTN_TOUCH'},
)


def device(keys, extra=None):
    return Mock(
        capabilities=Mock(return_value={1: keys, **(extra or {})}),
        active_keys=Mock(return_value=[]),
        input_props=Mock(return_value=[0]),
        info=SimpleNamespace(vendor=1, product=2, version=3, bustype=3),
    )


def event(kind, code, value=1):
    return SimpleNamespace(type=kind, code=code, value=value)


class CleaningTests(unittest.TestCase):
    def setUp(self):
        self.keyboard = device([1, 30, 115, 464], {4: [4]})
        self.mouse = device([272, 273], {2: [0, 1]})
        self.trackpad = device([330], {3: [(0, 'axis-info')]})
        self.hardware = {
            Path('/dev/input/event0'): self.keyboard,
            Path('/dev/input/event1'): self.mouse,
            Path('/dev/input/event2'): self.trackpad,
        }
        self.backend = SimpleNamespace(
            ecodes=CODES, InputDevice=lambda path: self.hardware[Path(path)], UInput=Mock(),
        )
        self.session = CleaningSession(self.backend)
        self.paths = patch('keyflip.cleaning.Path.glob', side_effect=lambda _: list(self.hardware))
        self.paths.start()
        self.addCleanup(self.paths.stop)
        self.addCleanup(self.session.close)

    def test_all_keyboard_endpoints_grabbed_but_mouse_and_trackpad_untouched(self):
        external = device([30])
        self.hardware[Path('/dev/input/event3')] = external
        self.session.scan()
        self.keyboard.grab.assert_called_once()
        external.grab.assert_called_once()
        self.mouse.grab.assert_not_called()
        self.trackpad.grab.assert_not_called()
        self.backend.UInput.assert_not_called()

    def test_combined_keyboard_pointer_filters_keys_and_preserves_pointer_events(self):
        combined = device([30, 115, 464, 272, 330], {2: [0, 1], 3: [(0, 'axis-info')], 4: [4, 5]})
        self.hardware[Path('/dev/input/event3')] = combined
        self.session.scan()
        capabilities = self.backend.UInput.call_args.args[0]
        self.assertEqual(capabilities[1], [272, 330])
        self.assertEqual(capabilities[3], [(0, 'axis-info')])
        self.assertEqual(capabilities[4], [5])
        pointer = self.backend.UInput.return_value
        keys = [event(1, 30), event(1, 115), event(1, 464), event(4, 4)]
        movement = [event(1, 272), event(1, 330), event(2, 0), event(3, 0), event(0, 0)]
        combined.read.return_value = keys + movement
        self.session.drain(combined, pointer)
        self.assertEqual([call.args[0] for call in pointer.write_event.call_args_list], movement)

    def test_hotplug_keyboard_is_grabbed_and_unplug_releases_handle(self):
        self.session.scan()
        external = device([30])
        path = Path('/dev/input/event3')
        self.hardware[path] = external
        self.session.scan()
        external.grab.assert_called_once()
        del self.hardware[path]
        self.session.scan()
        external.close.assert_called_once()

    def test_reused_event_number_is_grabbed_after_disconnect(self):
        self.session.scan()
        self.keyboard.read.side_effect = OSError(errno.ENODEV, 'Device disconnected')
        self.session.drain(self.keyboard, None)
        replacement = device([30])
        self.hardware[Path('/dev/input/event0')] = replacement
        self.session.scan()
        self.keyboard.close.assert_called_once()
        replacement.grab.assert_called_once()

    def test_no_keyboards_does_not_report_ready(self):
        del self.hardware[Path('/dev/input/event0')]
        ready = Mock()
        with self.assertRaisesRegex(RuntimeError, 'No keyboard'):
            self.session.run(object(), ready)
        ready.assert_not_called()

    def test_partial_failure_releases_every_grab(self):
        failure = device([30])
        failure.grab.side_effect = PermissionError('denied')
        self.hardware[Path('/dev/input/event3')] = failure
        ready = Mock()
        with self.assertRaises(PermissionError):
            self.session.run(object(), ready)
        ready.assert_not_called()
        self.keyboard.close.assert_called_once()
        failure.close.assert_called_once()
        self.assertFalse(self.session.devices)

    def test_held_keys_prevent_start(self):
        self.keyboard.active_keys.return_value = [30]
        with self.assertRaisesRegex(RuntimeError, 'Release all keys'):
            self.session.run(object(), Mock())
        self.keyboard.grab.assert_not_called()

    def test_stop_or_gui_disconnect_releases_keyboards(self):
        control = object()
        with patch('keyflip.cleaning.select.select', return_value=([control], [], [])):
            self.session.run(control, Mock())
        self.keyboard.close.assert_called_once()
        self.assertFalse(self.session.devices)

    def test_short_suspend_releases_keyboards_before_timeout(self):
        # One second asleep, no awake time elapsed: well below the 60s limit.
        # A blocking read would mean the session resumed suppressing input.
        with patch('keyflip.cleaning.time.clock_gettime', side_effect=[100, 101, 101]), \
             patch('keyflip.cleaning.time.monotonic', return_value=100), \
             patch('keyflip.cleaning.select.select', side_effect=AssertionError('Keyboards still blocked after resume')):
            self.session.run(object(), Mock())
        self.keyboard.close.assert_called_once()
        self.assertFalse(self.session.devices)

    def test_timeout_releases_keyboards(self):
        ready = Mock()
        with patch('keyflip.cleaning.time.clock_gettime', side_effect=[100, 161]):
            self.session.run(object(), ready)
        ready.assert_called_once()
        self.keyboard.close.assert_called_once()

    def test_event_overflow_releases_grabs(self):
        self.keyboard.read.return_value = [event(0, 3)]
        with patch('keyflip.cleaning.select.select', return_value=([self.keyboard], [], [])):
            with self.assertRaisesRegex(RuntimeError, 'events were lost'):
                self.session.run(object(), Mock())
        self.keyboard.close.assert_called_once()

    def test_pointer_setup_failure_does_not_grab_combined_device(self):
        combined = device([30, 272], {2: [0, 1]})
        self.hardware[Path('/dev/input/event3')] = combined
        self.backend.UInput.side_effect = OSError('uinput unavailable')
        with self.assertRaises(OSError):
            self.session.run(object(), Mock())
        combined.grab.assert_not_called()
        self.keyboard.close.assert_called_once()
