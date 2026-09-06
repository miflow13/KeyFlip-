"""GTK application lifecycle and command-line handling."""
import threading

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk

from .window import KeyboardWindow, SETTINGS_SCHEMA, load_css


def get_keyboard_window(application, present=False):
    if getattr(application, "quitting", False):
        return None
    window = next((window for window in application.get_windows()
                   if isinstance(window, KeyboardWindow)), None)
    if window is None:
        load_css()
        window = KeyboardWindow(application)
    window.settings.set_boolean("background-enabled", True)
    if present:
        window.present()
    return window


def on_activate(application):
    return get_keyboard_window(application, present=True)


def restore_keyboard_for_quit():
    status = KeyboardWindow.run_command("status")
    message = KeyboardWindow.result_message(status)
    if status.returncode != 0:
        if "No single supported i8042 internal keyboard found" in message:
            return None
        return message or "The keyboard status could not be checked."
    if "enabled" in message:
        return None
    result = KeyboardWindow.run_command("enable", privileged=True)
    if result.returncode != 0:
        return KeyboardWindow.result_message(result) or "Restoring Laptop Mode was cancelled or failed."
    status = KeyboardWindow.run_command("status")
    if status.returncode != 0 or "enabled" not in KeyboardWindow.result_message(status):
        return "The internal keyboard could not be confirmed enabled."
    return None


def request_quit(application):
    application.quitting = True
    application.hold()
    settings = Gio.Settings.new(SETTINGS_SCHEMA)
    settings.set_boolean("background-enabled", False)
    Gio.Settings.sync()
    cleaning = []
    for window in application.get_windows():
        if isinstance(window, KeyboardWindow):
            if window.cleaning_stop is not None:
                window.end_cleaning()
                cleaning.append(window.cleaning_done)
            window.close_safety_dialog()
            window.set_busy(True)

    def complete(error):
        application.quitting = False
        if error:
            window = on_activate(application)
            window.set_busy(False)
            window.show_toggle_result(
                1, f"KeyFlip is still running because Laptop Mode could not be restored. {error}"
            )
        else:
            settings.set_boolean("automatic-disable-owned", False)
            Gio.Settings.sync()
            application.quit()
        application.release()
        return GLib.SOURCE_REMOVE

    def restore():
        try:
            for done in cleaning:
                done.wait()
            error = restore_keyboard_for_quit()
        except Exception as error:
            GLib.idle_add(complete, str(error))
        else:
            GLib.idle_add(complete, error)

    threading.Thread(target=restore, daemon=True).start()


def on_command_line(application, command_line):
    options = command_line.get_options_dict()
    arguments = command_line.get_arguments()
    if getattr(application, "quitting", False):
        command_line.printerr_literal("KeyFlip is restoring Laptop Mode before quitting.\n")
        return 1
    if options.contains("quit") or "--quit" in arguments:
        if any(getattr(window, "busy", False) and getattr(window, "cleaning_stop", None) is None
               for window in application.get_windows()):
            command_line.printerr_literal("KeyFlip is changing modes. Try Quit again once it finishes.\n")
            return 1
        request_quit(application)
        return 0
    if options.contains("end-cleaning") or "--end-cleaning" in arguments:
        for window in application.get_windows():
            if isinstance(window, KeyboardWindow):
                window.end_cleaning()
        return 0
    preferences_requested = options.contains("preferences") or "--preferences" in arguments
    window = get_keyboard_window(application, present=not preferences_requested)
    if options.contains("cleaning") or "--cleaning" in arguments:
        if not window.busy:
            window.cleaning_mode_button.set_active(True)
        elif window.cleaning_stop is None:
            command_line.printerr_literal(
                "KeyFlip is changing modes. Try Cleaning Mode again once it finishes.\n"
            )
            return 1
    if preferences_requested:
        window.show_preferences()
    return 0


def create_application():
    application = Gtk.Application(
        application_id="io.github.miflow13.KeyFlip",
        flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
    )
    for option, description in (
        ("preferences", "Open Preferences"),
        ("quit", "Quit KeyFlip"),
        ("cleaning", "Start Cleaning Mode"),
        ("end-cleaning", "End Cleaning Mode"),
    ):
        application.add_main_option(
            option, 0, GLib.OptionFlags.NONE, GLib.OptionArg.NONE, description, None
        )
    application.connect("activate", on_activate)
    application.connect("command-line", on_command_line)
    return application


def run(argv):
    return create_application().run(argv)
