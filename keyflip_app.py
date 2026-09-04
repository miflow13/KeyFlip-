
import subprocess
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib, Gtk, Pango


APP_NAME = "KeyFlip"
VERSION = "0.1.0-beta"
SCRIPT = Path(__file__).resolve().with_name("keyflip-helper")
INSTALLED_SOUND_DIR = Path("/usr/share/keyflip/sounds")
SOURCE_SOUND_DIR = Path(__file__).resolve().parent / "assets" / "sounds"
SOUND_DIR = INSTALLED_SOUND_DIR if INSTALLED_SOUND_DIR.is_dir() else SOURCE_SOUND_DIR
PKEXEC = "/usr/bin/pkexec"


class KeyboardWindow(Gtk.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title=APP_NAME)
        self.set_icon_name("io.github.miflow13.KeyFlip")
        self.set_default_size(640, 390)
        self.set_resizable(False)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_margin_top(20)
        outer.set_margin_bottom(20)
        outer.set_margin_start(24)
        outer.set_margin_end(24)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        header_icon = Gtk.Image.new_from_icon_name("input-keyboard-symbolic")
        header_icon.set_pixel_size(28)
        header_icon.add_css_class("header-icon")
        header.append(header_icon)
        header_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        heading = Gtk.Label(label=APP_NAME, xalign=0)
        heading.add_css_class("title-1")
        subtitle = Gtk.Label(label=f"Internal keyboard control · {VERSION}", xalign=0)
        subtitle.add_css_class("dim-label")
        header_text.append(heading)
        header_text.append(subtitle)
        header.append(header_text)
        outer.append(header)

        self.status_frame = Gtk.Frame()
        self.status_frame.add_css_class("status-card")
        status_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        status_row.set_margin_top(13)
        status_row.set_margin_bottom(13)
        status_row.set_margin_start(18)
        status_row.set_margin_end(18)
        self.status_icon = Gtk.Image.new_from_icon_name("content-loading-symbolic")
        self.status_icon.set_pixel_size(38)
        self.status_icon.add_css_class("status-icon")
        self.status_icon_stack = Gtk.Overlay()
        self.status_icon_stack.set_size_request(46, 42)
        self.status_icon_stack.set_child(self.status_icon)
        self.status_badge = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
        self.status_badge.set_pixel_size(15)
        self.status_badge.set_halign(Gtk.Align.END)
        self.status_badge.set_valign(Gtk.Align.END)
        self.status_badge.add_css_class("status-badge")
        self.status_badge.set_visible(False)
        self.status_icon_stack.add_overlay(self.status_badge)
        status_row.append(self.status_icon_stack)
        status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        status_box.set_hexpand(True)
        self.state_label = Gtk.Label(label="Checking status...", xalign=0)
        self.state_label.add_css_class("title-3")
        self.detail_label = Gtk.Label(label="", xalign=0)
        self.detail_label.add_css_class("dim-label")
        self.detail_label.set_wrap(True)
        self.detail_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.detail_label.set_max_width_chars(46)
        status_box.append(self.state_label)
        status_box.append(self.detail_label)
        status_row.append(status_box)
        self.status_frame.set_child(status_row)
        outer.append(self.status_frame)

        safety_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        safety_box.add_css_class("safety-note")
        safety_icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
        safety_icon.set_pixel_size(18)
        safety_box.append(safety_icon)
        safety_label = Gtk.Label(
            label="Keep an external keyboard connected while the internal keyboard is disabled.",
            xalign=0,
        )
        safety_label.set_wrap(True)
        safety_label.set_hexpand(True)
        safety_box.append(safety_label)

        switch_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        switch_card.add_css_class("switch-card")
        switch_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        switch_text.set_hexpand(True)
        switch_title = Gtk.Label(label="Keyboard toggle", xalign=0)
        switch_title.add_css_class("title-3")
        self.switch_hint = Gtk.Label(label="Checking keyboard state…", xalign=0)
        self.switch_hint.add_css_class("dim-label")
        switch_text.append(switch_title)
        switch_text.append(self.switch_hint)
        switch_card.append(switch_text)
        self.toggle_switch = Gtk.Switch()
        self.toggle_switch.set_valign(Gtk.Align.CENTER)
        self.toggle_switch.set_size_request(146, 74)
        self.toggle_switch.add_css_class("large-switch")
        self.toggle_switch.set_tooltip_text("Enable or disable the internal keyboard")
        self.toggle_switch.connect("state-set", self.toggle_keyboard)
        switch_card.append(self.toggle_switch)
        outer.append(switch_card)
        outer.append(safety_box)

        self.refresh_button = Gtk.Button(label="Refresh status")
        self.refresh_button.add_css_class("flat")
        self.refresh_button.connect("clicked", lambda _: self.refresh_status())
        outer.append(self.refresh_button)

        self.set_child(outer)
        self.keyboard_enabled = None
        self.updating_switch = False
        self.busy = False
        self.refresh_status()
        self.status_timer = GLib.timeout_add_seconds(1, self.sync_status)
        self.connect("close-request", self.stop_status_sync)

    @staticmethod
    def run_command(*arguments, privileged=False):
        command = [str(SCRIPT), *arguments]
        if privileged:
            command.insert(0, PKEXEC)
        try:
            return subprocess.run(command, capture_output=True, text=True, check=False)
        except OSError as error:
            return subprocess.CompletedProcess(command, 1, "", str(error))

    @staticmethod
    def result_message(result):
        return (result.stdout or result.stderr).strip()

    def set_busy(self, busy):
        self.busy = busy
        self.toggle_switch.set_sensitive(not busy)
        self.refresh_button.set_sensitive(not busy)
        if busy:
            self.switch_hint.set_text("Waiting for authorization…")

    def sync_status(self):
        if not self.busy:
            self.refresh_status()
        return GLib.SOURCE_CONTINUE

    def stop_status_sync(self, _window):
        if self.status_timer:
            GLib.source_remove(self.status_timer)
            self.status_timer = None
        return False

    def refresh_status(self):
        result = self.run_command("status")
        message = self.result_message(result)
        if result.returncode == 0:
            self.keyboard_enabled = "enabled" in message
            self.state_label.set_text("Keyboard enabled" if self.keyboard_enabled else "Keyboard disabled")
            self.state_label.remove_css_class("state-enabled")
            self.state_label.remove_css_class("state-disabled")
            self.state_label.add_css_class(
                "state-enabled" if self.keyboard_enabled else "state-disabled"
            )
            self.detail_label.set_text(
                "Ready to type on this device."
                if self.keyboard_enabled
                else "Input from the laptop keyboard is blocked."
            )
            self.status_icon.set_from_icon_name(
                "input-keyboard-symbolic"
                if self.keyboard_enabled
                else "action-unavailable-symbolic"
            )
            self.status_badge.set_visible(self.keyboard_enabled)
            self.updating_switch = True
            self.toggle_switch.set_active(self.keyboard_enabled)
            self.toggle_switch.set_state(self.keyboard_enabled)
            self.updating_switch = False
            self.switch_hint.set_text("On" if self.keyboard_enabled else "Off")
            self.toggle_switch.set_sensitive(True)
            self.status_frame.remove_css_class("error")
        else:
            self.keyboard_enabled = None
            self.state_label.set_text("Status unavailable")
            self.state_label.remove_css_class("state-enabled")
            self.state_label.remove_css_class("state-disabled")
            self.detail_label.set_text(message or "The keyboard status could not be read.")
            self.status_icon.set_from_icon_name("dialog-error-symbolic")
            self.status_badge.set_visible(False)
            self.switch_hint.set_text("Status unavailable")
            self.toggle_switch.set_sensitive(False)
            self.status_frame.add_css_class("error")

    def toggle_keyboard(self, _switch, requested_state):
        if self.updating_switch:
            return False
        if self.keyboard_enabled is None:
            self.refresh_status()
            return True
        action = "enable" if requested_state else "disable"
        if requested_state == self.keyboard_enabled:
            return False
        self.play_toggle_sound(requested_state)
        self.set_busy(True)
        threading.Thread(target=self.finish_toggle, args=(action,), daemon=True).start()
        # Keep the thumb in its confirmed position until the privileged action succeeds.
        return True

    def finish_toggle(self, action):
        result = self.run_command(action, privileged=True)
        message = self.result_message(result) or "Toggle cancelled or failed."
        if result.returncode != 0 and (
            "request dismissed" in message.lower()
            or "not authorized" in message.lower()
            or "authentication" in message.lower()
        ):
            message = (
                "Authorization was cancelled or the password was not accepted. "
                "Use the external keyboard to enter your login password, then try again."
            )
        if result.returncode == 0:
            status = self.run_command("status")
            expected = "enabled" if action == "enable" else "disabled"
            actual = self.result_message(status)
            if status.returncode != 0 or expected not in actual:
                result = subprocess.CompletedProcess(result.args, 1, result.stdout, result.stderr)
                message = f"The command completed, but the keyboard is still not {expected}. {actual}"
        GLib.idle_add(self.show_toggle_result, result.returncode, message)

    @staticmethod
    def play_toggle_sound(enabled):
        sound_file = SOUND_DIR / ("toggle-on.ogg" if enabled else "toggle-off.ogg")
        try:
            subprocess.Popen(
                [
                    "/usr/bin/canberra-gtk-play",
                    f"--file={sound_file}",
                    f"--description=KeyFlip {'on' if enabled else 'off'}",
                    "--cache-control=never",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            pass

    def show_toggle_result(self, returncode, message):
        self.set_busy(False)
        if returncode == 0:
            self.refresh_status()
        else:
            self.state_label.set_text("Keyboard change failed")
            self.state_label.remove_css_class("state-enabled")
            self.state_label.remove_css_class("state-disabled")
            self.detail_label.set_text(message)
            self.status_icon.set_from_icon_name("dialog-error-symbolic")
            self.status_badge.set_visible(False)
            self.status_frame.add_css_class("error")
            self.switch_hint.set_text("Change failed — try again")
            self.toggle_switch.set_sensitive(True)
        return GLib.SOURCE_REMOVE


def load_css():
    provider = Gtk.CssProvider()
    provider.load_from_data(b"""
        window {
            background: @window_bg_color;
            color: @window_fg_color;
        }
        .header-icon {
            color: @accent_color;
            background: alpha(@accent_color, 0.12);
            border-radius: 12px;
            padding: 8px;
        }
        .status-card {
            border-radius: 14px;
            border: 1px solid @borders;
            background: @card_bg_color;
            box-shadow: 0 2px 8px alpha(black, 0.08);
        }
        .status-card.error {
            border-color: @error_color;
            background: alpha(@error_color, 0.08);
        }
        .status-icon { color: @accent_color; }
        .status-badge {
            color: white;
            background: #2e9b55;
            border: 2px solid @card_bg_color;
            border-radius: 12px;
            padding: 2px;
        }
        .status-card.error .status-icon { color: @error_color; }
        .state-enabled { color: #2e9b55; }
        .state-disabled { color: #d94b4b; }
        .safety-note {
            color: @window_fg_color;
            background: alpha(@warning_color, 0.12);
            border-radius: 10px;
            padding: 9px 12px;
        }
        .safety-note image { color: @warning_color; }
        .switch-card {
            background: @card_bg_color;
            border: 1px solid @borders;
            border-radius: 14px;
            padding: 10px 18px;
        }
        switch.large-switch {
            min-width: 132px;
            min-height: 64px;
            border-radius: 36px;
        }
        switch.large-switch slider {
            min-width: 56px;
            min-height: 56px;
            border-radius: 30px;
            margin: 4px;
        }
        button { border-radius: 8px; }
        .dim-label { opacity: 0.68; }
    """)
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


def on_activate(application):
    load_css()
    KeyboardWindow(application).present()


app = Gtk.Application(application_id="io.github.miflow13.KeyFlip")
app.connect("activate", on_activate)


if __name__ == "__main__":
    app.run(None)
