import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import Clutter from 'gi://Clutter';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const HELPER = '/usr/libexec/keyflip/keyflip-helper';
const SOUND_DIR = '/usr/share/keyflip/sounds';

const KeyFlipIndicator = GObject.registerClass(
class KeyFlipIndicator extends St.Button {
    _init(extensionPath) {
        super._init({
            style_class: 'panel-button keyflip-panel-button',
            reactive: true,
            can_focus: true,
            track_hover: true,
            accessible_name: 'KeyFlip internal keyboard toggle',
        });

        this._extensionPath = extensionPath;
        this._keyboardIcon = new St.Icon({
            style_class: 'keyflip-keyboard-icon',
        });
        this.set_child(this._keyboardIcon);
        this.connect('clicked', () => this._toggle());
        this._refresh();
        this._statusTimer = GLib.timeout_add_seconds(
            GLib.PRIORITY_DEFAULT,
            1,
            () => {
                if (!this._busy)
                    this._refresh();
                return GLib.SOURCE_CONTINUE;
            }
        );
        this.connect('destroy', () => {
            if (this._statusTimer) {
                GLib.source_remove(this._statusTimer);
                this._statusTimer = null;
            }
        });
    }

    _run(argv) {
        try {
            const process = Gio.Subprocess.new(
                argv,
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE
            );
            const [, stdout, stderr] = process.communicate_utf8(null, null);
            return [process.get_successful(), (stdout || stderr || '').trim()];
        } catch (error) {
            return [false, error.message];
        }
    }

    _refresh() {
        const [success, output] = this._run([HELPER, 'status']);
        if (!success) {
            this._keyboardIcon.gicon = null;
            this._keyboardIcon.icon_name = 'dialog-error-symbolic';
            this.accessible_name = `KeyFlip: ${output || 'status unavailable'}`;
            return;
        }

        this._enabled = output.includes('enabled');
        this._keyboardIcon.icon_name = null;
        this._keyboardIcon.gicon = Gio.icon_new_for_string(
            `${this._extensionPath}/keyboard-${this._enabled ? 'enabled' : 'disabled'}.svg`
        );
        this.accessible_name = `Internal keyboard ${this._enabled ? 'enabled' : 'disabled'}`;
    }

    _toggle() {
        if (this._busy)
            return;

        this._busy = true;
        const enabling = !this._enabled;
        this._playSound(enabling);
        this._keyboardIcon.opacity = 130;

        GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, () => {
            const [success, output] = this._run([
                '/usr/bin/pkexec',
                HELPER,
                enabling ? 'enable' : 'disable',
            ]);
            this._busy = false;
            this._keyboardIcon.opacity = 255;
            this._refresh();
            if (success)
                this._showStatus(enabling);
            else
                Main.notify('KeyFlip could not change the keyboard', output);
            return GLib.SOURCE_REMOVE;
        });
    }

    _showStatus(enabled) {
        const icon = Gio.icon_new_for_string(
            `${this._extensionPath}/keyboard-${enabled ? 'enabled' : 'disabled'}.svg`
        );
        const label = `Keyboard ${enabled ? 'enabled' : 'disabled'}`;
        try {
            const osdManager = Main.osdWindowManager;
            const monitorIndex = Main.layoutManager.primaryIndex;
            const osdWindow = osdManager._osdWindows?.[monitorIndex];
            const previousAlignment = osdWindow?.y_align;

            // GNOME places OSDs near the bottom by default. Center only the
            // KeyFlip message, then restore the normal position once it fades.
            if (osdWindow)
                osdWindow.y_align = Clutter.ActorAlign.CENTER;

            const showOsd = osdManager.showOne ?? osdManager.show;
            showOsd.call(osdManager, monitorIndex, icon, label, null);

            if (osdWindow) {
                GLib.timeout_add(GLib.PRIORITY_DEFAULT, 2500, () => {
                    osdWindow.y_align = previousAlignment;
                    return GLib.SOURCE_REMOVE;
                });
            }
        } catch (_error) {
            Main.notify('KeyFlip', label);
        }
    }

    _playSound(enabling) {
        const sound = `${SOUND_DIR}/toggle-${enabling ? 'on' : 'off'}.ogg`;
        try {
            Gio.Subprocess.new(
                [
                    '/usr/bin/canberra-gtk-play',
                    `--file=${sound}`,
                    `--description=KeyFlip ${enabling ? 'on' : 'off'}`,
                    '--cache-control=never',
                ],
                Gio.SubprocessFlags.NONE
            );
        } catch (_error) {
            // Sound feedback is optional.
        }
    }
});

export default class KeyFlipExtension extends Extension {
    enable() {
        this._indicator = new KeyFlipIndicator(this.path);
        Main.panel._rightBox.insert_child_at_index(this._indicator, 0);
    }

    disable() {
        this._indicator?.destroy();
        this._indicator = null;
    }
}
