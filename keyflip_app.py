
import subprocess
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk, Pango


APP_NAME = "KeyFlip"
VERSION = "0.2.0-beta"
SCRIPT = Path(__file__).resolve().with_name("keyflip-helper")
INSTALLED_SOUND_DIR = Path("/usr/share/keyflip/sounds")
SOURCE_SOUND_DIR = Path(__file__).resolve().parent / "assets" / "sounds"
SOUND_DIR = INSTALLED_SOUND_DIR if INSTALLED_SOUND_DIR.is_dir() else SOURCE_SOUND_DIR
PKEXEC = "/usr/bin/pkexec"
SETTINGS_SCHEMA = "io.github.miflow13.KeyFlip"


class KeyboardWindow(Gtk.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title=APP_NAME)
        self.set_icon_name("io.github.miflow13.KeyFlip")
        self.settings = Gio.Settings.new(SETTINGS_SCHEMA)
        self.set_default_size(680, 680)
        self.set_resizable(False)

        header = Gtk.HeaderBar()
        header.add_css_class("app-header")
        header_title = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header_icon = Gtk.Image.new_from_icon_name("input-keyboard-symbolic")
        header_icon.set_pixel_size(24)
        header_icon.add_css_class("header-icon")
        header_title.append(header_icon)
        header_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        heading = Gtk.Label(label=APP_NAME, xalign=0)
        heading.add_css_class("title-1")
        subtitle = Gtk.Label(label="Laptop keyboard control", xalign=0)
        subtitle.add_css_class("dim-label")
        header_text.append(heading)
        header_text.append(subtitle)
        header_title.append(header_text)
        header.pack_start(header_title)
        self.refresh_button = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        self.refresh_button.add_css_class("flat")
        self.refresh_button.add_css_class("circular")
        self.refresh_button.set_tooltip_text("Refresh keyboard status")
        self.refresh_button.connect("clicked", lambda _: self.refresh_status())
        header.pack_end(self.refresh_button)
        self.set_titlebar(header)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        outer.set_margin_top(24)
        outer.set_margin_bottom(24)
        outer.set_margin_start(30)
        outer.set_margin_end(30)

        setup_label = Gtk.Label(label="Choose a mode", xalign=0)
        setup_label.add_css_class("section-label")
        outer.append(setup_label)

        mode_selector = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        mode_selector.add_css_class("mode-selector")
        mode_selector.set_homogeneous(True)
        self.laptop_mode_button = self.create_mode_button(
            "computer-symbolic", "Laptop Mode", "Built-in input enabled"
        )
        self.desk_mode_button = self.create_mode_button(
            "input-keyboard-symbolic", "Desk Mode", "Built-in keyboard off"
        )
        self.desk_mode_button.set_group(self.laptop_mode_button)
        self.laptop_mode_button.connect(
            "toggled", self.on_mode_selected, True
        )
        self.desk_mode_button.connect(
            "toggled", self.on_mode_selected, False
        )
        mode_selector.append(self.laptop_mode_button)
        mode_selector.append(self.desk_mode_button)
        outer.append(mode_selector)

        self.status_frame = Gtk.Frame()
        self.status_frame.add_css_class("device-card")
        card_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        status_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        status_row.add_css_class("status-row")
        self.status_icon = Gtk.Image.new_from_icon_name("content-loading-symbolic")
        self.status_icon.set_pixel_size(32)
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
        self.external_badge = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        self.external_badge.add_css_class("external-badge")
        self.external_badge.set_valign(Gtk.Align.CENTER)
        external_icon = Gtk.Image.new_from_icon_name("input-keyboard-symbolic")
        external_icon.set_pixel_size(16)
        self.external_label = Gtk.Label(label="External keyboard connected")
        self.external_badge.append(external_icon)
        self.external_badge.append(self.external_label)
        self.external_badge.set_visible(False)
        status_row.append(self.external_badge)
        card_content.append(status_row)
        self.status_frame.set_child(card_content)
        outer.append(self.status_frame)

        controls_frame = Gtk.Frame()
        controls_frame.add_css_class("controls-card")
        controls = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        keyboard_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        keyboard_row.add_css_class("device-row")
        keyboard_icon = Gtk.Image.new_from_icon_name("input-keyboard-symbolic")
        keyboard_icon.set_pixel_size(20)
        keyboard_row.append(keyboard_icon)
        keyboard_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        keyboard_text.set_hexpand(True)
        keyboard_title = Gtk.Label(label="Internal keyboard", xalign=0)
        keyboard_title.add_css_class("title-3")
        keyboard_description = Gtk.Label(label="Control the built-in keyboard", xalign=0)
        keyboard_description.add_css_class("dim-label")
        keyboard_text.append(keyboard_title)
        keyboard_text.append(keyboard_description)
        keyboard_row.append(keyboard_text)
        self.keyboard_switch = Gtk.Switch()
        self.keyboard_switch.set_valign(Gtk.Align.CENTER)
        self.keyboard_switch.connect("state-set", self.on_keyboard_switch)
        keyboard_row.append(self.keyboard_switch)
        self.device_state = Gtk.Label(label="Checking…")
        self.device_state.add_css_class("device-value")
        keyboard_row.append(self.device_state)
        controls.append(keyboard_row)
        controls.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        automatic_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        automatic_row.add_css_class("device-row")
        automatic_icon = Gtk.Image.new_from_icon_name("emblem-synchronizing-symbolic")
        automatic_icon.set_pixel_size(20)
        automatic_row.append(automatic_icon)
        automatic_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        automatic_text.set_hexpand(True)
        automatic_title = Gtk.Label(label="Automatic mode switching", xalign=0)
        automatic_title.add_css_class("title-3")
        automatic_description = Gtk.Label(
            label="Switch when an external keyboard connects or disconnects", xalign=0
        )
        automatic_description.add_css_class("dim-label")
        automatic_text.append(automatic_title)
        automatic_text.append(automatic_description)
        automatic_row.append(automatic_text)
        self.automatic_switch = Gtk.Switch(
            active=self.settings.get_boolean("automatic-mode-switching")
        )
        self.automatic_switch.set_valign(Gtk.Align.CENTER)
        self.automatic_switch.connect("notify::active", self.on_automatic_switch_changed)
        automatic_row.append(self.automatic_switch)
        controls.append(automatic_row)
        controls_frame.set_child(controls)
        outer.append(controls_frame)

        safety_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
        safety_box.add_css_class("safety-note")
        safety_icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
        safety_icon.set_pixel_size(16)
        safety_box.append(safety_icon)
        safety_label = Gtk.Label(
            label="Keep an external keyboard connected while this one is off.",
            xalign=0,
        )
        safety_label.set_wrap(True)
        safety_label.set_hexpand(True)
        safety_box.append(safety_label)
        outer.append(safety_box)

        self.set_child(outer)
        self.keyboard_enabled = None
        self.updating_mode = False
        self.busy = False
        self.refreshing = False
        self.safety_dialog = None
        self.refresh_status()
        self.status_timer = GLib.timeout_add_seconds(1, self.sync_status)
        self.connect("close-request", self.stop_status_sync)

    @staticmethod
    def create_mode_button(icon_name, title, description):
        button = Gtk.ToggleButton()
        button.add_css_class("mode-button")
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(24)
        title_label = Gtk.Label(label=title)
        title_label.add_css_class("title-3")
        description_label = Gtk.Label(label=description)
        description_label.add_css_class("dim-label")
        content.append(icon)
        content.append(title_label)
        content.append(description_label)
        button.set_child(content)
        return button

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
        self.laptop_mode_button.set_sensitive(not busy)
        self.desk_mode_button.set_sensitive(not busy)
        self.keyboard_switch.set_sensitive(not busy)
        self.refresh_button.set_sensitive(not busy)
        if busy:
            self.device_state.set_text("Applying…")

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
        if self.refreshing or self.busy:
            return
        self.refreshing = True
        threading.Thread(target=self.finish_status_refresh, daemon=True).start()

    def finish_status_refresh(self):
        result = self.run_command("status")
        external = self.run_command("external-list")
        GLib.idle_add(self.apply_status_refresh, result, external)

    def apply_status_refresh(self, result, external):
        self.refreshing = False
        external_connected = external.returncode == 0 and bool(external.stdout.strip())
        self.external_badge.set_visible(external_connected)
        message = self.result_message(result)
        if result.returncode == 0:
            self.keyboard_enabled = "enabled" in message
            self.state_label.set_text(
                "Laptop Mode active" if self.keyboard_enabled else "Desk Mode active"
            )
            self.state_label.remove_css_class("state-enabled")
            self.state_label.remove_css_class("state-disabled")
            self.state_label.add_css_class(
                "state-enabled" if self.keyboard_enabled else "state-disabled"
            )
            self.detail_label.set_text(
                "Built-in keyboard ready for portable use."
                if self.keyboard_enabled
                else "Built-in keyboard input is blocked."
            )
            self.status_icon.set_from_icon_name(
                "computer-symbolic"
                if self.keyboard_enabled
                else "input-keyboard-symbolic"
            )
            self.status_badge.set_visible(True)
            self.sync_mode_controls()
            self.device_state.set_text("On" if self.keyboard_enabled else "Off")
            self.device_state.remove_css_class("off")
            if not self.keyboard_enabled:
                self.device_state.add_css_class("off")
            self.laptop_mode_button.set_sensitive(True)
            self.desk_mode_button.set_sensitive(True)
            self.keyboard_switch.set_sensitive(True)
            self.status_frame.remove_css_class("error")
        else:
            self.keyboard_enabled = None
            self.state_label.set_text("Status unavailable")
            self.state_label.remove_css_class("state-enabled")
            self.state_label.remove_css_class("state-disabled")
            self.detail_label.set_text(message or "The keyboard status could not be read.")
            self.status_icon.set_from_icon_name("dialog-error-symbolic")
            self.status_badge.set_visible(False)
            self.device_state.set_text("Unavailable")
            self.laptop_mode_button.set_sensitive(False)
            self.desk_mode_button.set_sensitive(False)
            self.keyboard_switch.set_sensitive(False)
            self.status_frame.add_css_class("error")
        return GLib.SOURCE_REMOVE

    def sync_mode_controls(self):
        self.updating_mode = True
        self.laptop_mode_button.set_active(bool(self.keyboard_enabled))
        self.desk_mode_button.set_active(self.keyboard_enabled is False)
        self.keyboard_switch.set_active(bool(self.keyboard_enabled))
        self.keyboard_switch.set_state(bool(self.keyboard_enabled))
        self.updating_mode = False

    def on_mode_selected(self, button, keyboard_enabled):
        if self.updating_mode or not button.get_active():
            return
        if self.keyboard_enabled is None:
            self.refresh_status()
            return
        if keyboard_enabled == self.keyboard_enabled:
            return

        self.request_keyboard_state(keyboard_enabled)

    def on_keyboard_switch(self, _switch, keyboard_enabled):
        if self.updating_mode:
            return False
        self.request_keyboard_state(keyboard_enabled)
        return True

    def on_automatic_switch_changed(self, switch, _property):
        enabled = switch.get_active()
        self.settings.set_boolean("automatic-mode-switching", enabled)
        if not enabled:
            self.settings.set_boolean("automatic-disable-owned", False)

    def request_keyboard_state(self, keyboard_enabled):
        if self.keyboard_enabled is None:
            self.refresh_status()
            return
        if keyboard_enabled == self.keyboard_enabled:
            return

        self.settings.set_boolean("automatic-disable-owned", False)

        # Keep the selected preset tied to confirmed device state.
        self.sync_mode_controls()
        action = "enable" if keyboard_enabled else "disable"

        if action == "disable":
            external = self.run_command("external-list")
            external_connected = external.returncode == 0 and bool(external.stdout.strip())
            if not external_connected:
                GLib.idle_add(self.show_disable_warning)
                return

        self.start_toggle(action, keyboard_enabled)

    def show_disable_warning(self):
        if self.safety_dialog is not None:
            self.safety_dialog.present()
            return GLib.SOURCE_REMOVE

        dialog = Gtk.Window(
            title="Keyboard safety",
            transient_for=self,
            modal=True,
            resizable=False,
        )
        dialog.set_default_size(420, -1)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_top(24)
        content.set_margin_bottom(20)
        content.set_margin_start(24)
        content.set_margin_end(24)

        warning_icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
        warning_icon.set_pixel_size(36)
        warning_icon.add_css_class("warning-dialog-icon")
        content.append(warning_icon)

        title = Gtk.Label(label="No external keyboard detected")
        title.add_css_class("title-2")
        content.append(title)

        message = Gtk.Label(
            label=(
                "Desk Mode will disable your laptop keyboard. Connect an external "
                "keyboard first, or you may be unable to type."
            )
        )
        message.set_wrap(True)
        message.set_justify(Gtk.Justification.CENTER)
        message.add_css_class("dim-label")
        content.append(message)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        actions.set_halign(Gtk.Align.END)
        cancel = Gtk.Button(label="Cancel")
        cancel.connect("clicked", lambda _button: self.close_safety_dialog())
        confirm = Gtk.Button(label="Activate Anyway")
        confirm.add_css_class("destructive-action")
        confirm.connect("clicked", lambda _button: self.confirm_unsafe_disable())
        actions.append(cancel)
        actions.append(confirm)
        content.append(actions)

        dialog.set_child(content)
        dialog.connect("close-request", self.on_safety_dialog_closed)
        self.safety_dialog = dialog
        dialog.present()
        return GLib.SOURCE_REMOVE

    def close_safety_dialog(self):
        if self.safety_dialog is not None:
            self.safety_dialog.destroy()
            self.safety_dialog = None

    def on_safety_dialog_closed(self, _dialog):
        self.safety_dialog = None
        return False

    def confirm_unsafe_disable(self):
        self.close_safety_dialog()
        if self.keyboard_enabled:
            self.start_toggle("disable", False)

    def start_toggle(self, action, requested_state):
        self.play_toggle_sound(requested_state)
        self.set_busy(True)
        threading.Thread(target=self.finish_toggle, args=(action,), daemon=True).start()

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
            self.device_state.set_text("Change failed")
            self.sync_mode_controls()
            self.laptop_mode_button.set_sensitive(True)
            self.desk_mode_button.set_sensitive(True)
            self.keyboard_switch.set_sensitive(True)
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
            background: alpha(@accent_color, 0.14);
            border-radius: 13px;
            padding: 11px;
        }
        .section-label {
            font-weight: 700;
            opacity: 0.72;
            margin-top: 2px;
        }
        .mode-selector { margin-bottom: 2px; }
        button.mode-button {
            min-height: 126px;
            padding: 18px;
            border-radius: 14px;
            border: 1px solid @borders;
            background: @card_bg_color;
            box-shadow: none;
        }
        button.mode-button:hover {
            background: alpha(@accent_color, 0.08);
        }
        button.mode-button:checked {
            color: @accent_color;
            border-color: alpha(@accent_color, 0.75);
            background: alpha(@accent_color, 0.14);
            box-shadow: inset 0 0 0 1px alpha(@accent_color, 0.22);
        }
        .device-card {
            border-radius: 16px;
            border: 1px solid @borders;
            background: @card_bg_color;
            box-shadow: 0 3px 12px alpha(black, 0.08);
        }
        .device-card.error {
            border-color: @error_color;
            background: alpha(@error_color, 0.08);
        }
        .status-row { padding: 20px; }
        .status-icon { color: @accent_color; }
        .status-badge {
            color: white;
            background: #2e9b55;
            border: 2px solid @card_bg_color;
            border-radius: 12px;
            padding: 2px;
        }
        .device-card.error .status-icon { color: @error_color; }
        .state-enabled, .state-disabled { color: @accent_color; }
        .external-badge {
            color: @accent_color;
            background: alpha(@accent_color, 0.12);
            border-radius: 12px;
            padding: 8px 12px;
        }
        .controls-card {
            border-radius: 16px;
            border: 1px solid @borders;
            background: @card_bg_color;
            box-shadow: 0 3px 12px alpha(black, 0.08);
        }
        .controls-card separator {
            background: @borders;
            margin-left: 20px;
            margin-right: 20px;
        }
        .device-row { padding: 14px 20px; }
        .device-row > image { color: alpha(@window_fg_color, 0.78); }
        .device-value {
            min-width: 32px;
            opacity: 0.82;
        }
        .safety-note {
            color: alpha(@window_fg_color, 0.72);
            background: alpha(@window_fg_color, 0.05);
            border: 1px solid @borders;
            border-radius: 12px;
            padding: 10px 14px;
        }
        .safety-note image {
            color: @warning_color;
            opacity: 0.85;
        }
        .warning-dialog-icon { color: @warning_color; }
        button { border-radius: 10px; }
        .dim-label { opacity: 0.68; }
    """)
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


def on_activate(application):
    window = application.get_active_window()
    if window is None:
        load_css()
        window = KeyboardWindow(application)
    window.present()


app = Gtk.Application(application_id="io.github.miflow13.KeyFlip")
app.connect("activate", on_activate)


if __name__ == "__main__":
    app.run(None)
