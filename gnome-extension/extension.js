import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import Clutter from 'gi://Clutter';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as ModalDialog from 'resource:///org/gnome/shell/ui/modalDialog.js';

const HELPER = '/usr/libexec/keyflip/keyflip-helper';
const SOUND_DIR = '/usr/share/keyflip/sounds';
const SETTINGS_SCHEMA = 'io.github.miflow13.KeyFlip';

// Clutter does not expose libadwaita's SpringAnimation, so these keyframes
// approximate SpringParams.new(0.75, 1.7, 100.0) with initial_velocity -18.8.
const TOGGLE_SPRING_KEYFRAMES = [
    {scale: 0.82, duration: 55},
    {scale: 1.20, duration: 120},
    {scale: 0.94, duration: 95},
    {scale: 1.05, duration: 80},
    {scale: 1.00, duration: 70},
];

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
        this._settings = new Gio.Settings({schema_id: SETTINGS_SCHEMA});
        this._keyboardIcon = new St.Icon({
            style_class: 'keyflip-keyboard-icon',
        });
        this._keyboardIcon.set_pivot_point(0.5, 0.5);
        this.set_child(this._keyboardIcon);
        this.connect('clicked', () => this._toggle());
        this._refresh();
        this._externalKeyboardIds = new Set();
        this._externalKeyboardKnown = false;
        this._disconnectChecks = 0;
        this._checkExternalKeyboard();
        this._statusTimer = GLib.timeout_add_seconds(
            GLib.PRIORITY_DEFAULT,
            1,
            () => {
                if (!this._busy && !this._statusCheckRunning) {
                    this._statusCheckRunning = true;
                    this._refresh().finally(() => {
                        this._statusCheckRunning = false;
                    });
                }
                return GLib.SOURCE_CONTINUE;
            }
        );
        this._deviceTimer = GLib.timeout_add(
            GLib.PRIORITY_DEFAULT,
            500,
            () => {
                if (!this._deviceCheckRunning) {
                    this._deviceCheckRunning = true;
                    this._checkExternalKeyboard().finally(() => {
                        this._deviceCheckRunning = false;
                    });
                }
                return GLib.SOURCE_CONTINUE;
            }
        );
        this.connect('destroy', () => {
            this._destroyed = true;
            if (this._statusTimer) {
                GLib.source_remove(this._statusTimer);
                this._statusTimer = null;
            }
            if (this._deviceTimer) {
                GLib.source_remove(this._deviceTimer);
                this._deviceTimer = null;
            }
        });
    }

    _runAsync(argv) {
        return new Promise(resolve => {
            let process;
            try {
                process = Gio.Subprocess.new(
                    argv,
                    Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE
                );
            } catch (error) {
                resolve([false, error.message]);
                return;
            }

            process.communicate_utf8_async(null, null, (source, result) => {
                try {
                    const [, stdout, stderr] = source.communicate_utf8_finish(result);
                    resolve([
                        source.get_successful(),
                        (stdout || stderr || '').trim(),
                    ]);
                } catch (error) {
                    resolve([false, error.message]);
                }
            });
        });
    }

    async _refresh() {
        const [success, output] = await this._runAsync([HELPER, 'status']);
        if (this._destroyed)
            return;
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

    async _toggle() {
        if (this._busy)
            return;

        // A manual choice ends the current automatic disable cycle.
        this._settings.set_boolean('automatic-disable-owned', false);
        const enabling = !this._enabled;
        if (!enabling) {
            const [success, output] = await this._runAsync([HELPER, 'external-list']);
            if (this._destroyed)
                return;
            if (!success || !output) {
                this._confirmDisableWithoutExternalKeyboard();
                return;
            }
        }
        this._setEnabled(enabling);
    }

    _confirmDisableWithoutExternalKeyboard() {
        const dialog = new ModalDialog.ModalDialog();
        const title = new St.Label({
            text: 'No external keyboard detected',
            style_class: 'headline',
        });
        const message = new St.Label({
            text: 'Connect an external keyboard before disabling the internal keyboard, or you may be unable to type.',
            style_class: 'message-dialog-description',
        });
        message.clutter_text.line_wrap = true;
        dialog.contentLayout.add_child(title);
        dialog.contentLayout.add_child(message);
        dialog.setButtons([
            {
                label: 'Cancel',
                action: () => dialog.close(),
                key: Clutter.KEY_Escape,
            },
            {
                label: 'Disable Anyway',
                action: () => {
                    dialog.close();
                    this._setEnabled(false);
                },
                default: true,
            },
        ]);
        dialog.open();
    }

    async _checkExternalKeyboard() {
        const [success, output] = await this._runAsync([HELPER, 'external-list']);
        if (this._destroyed)
            return;
        if (!success)
            return;

        const keyboardIds = new Set(output ? output.split('\n') : []);
        const connected = keyboardIds.size > 0;
        const wasKnown = this._externalKeyboardKnown;
        const wasConnected = this._externalKeyboardIds.size > 0;
        if (!connected && wasKnown && wasConnected) {
            this._disconnectChecks++;
            if (this._disconnectChecks < 2)
                return;
        } else {
            this._disconnectChecks = 0;
        }
        this._externalKeyboardKnown = true;
        this._externalKeyboardIds = keyboardIds;

        if (!this._settings.get_boolean('automatic-mode-switching'))
            return;

        if (connected && this._enabled && !this._busy) {
            this._setEnabled(false, true);
        }
        else if (!connected && wasKnown && wasConnected &&
                 this._settings.get_boolean('automatic-disable-owned') &&
                 !this._enabled && !this._busy)
            this._setEnabled(true, true);
    }

    async _setEnabled(enabling, automatic = false) {
        this._busy = true;
        this._playSound(enabling);
        this._playToggleAnimation();
        this._keyboardIcon.opacity = 130;

        const [success, output] = await this._runAsync([
            '/usr/bin/pkexec',
            HELPER,
            enabling ? 'enable' : 'disable',
        ]);
        if (this._destroyed)
            return;
        this._busy = false;
        this._keyboardIcon.opacity = 255;
        this._refresh();
        if (success) {
            if (automatic)
                this._settings.set_boolean('automatic-disable-owned', !enabling);
            this._showStatus(enabling);
        } else {
            if (automatic)
                this._settings.set_boolean('automatic-disable-owned', false);
            Main.notify(
                automatic ? `KeyFlip could not auto-${enabling ? 'enable' : 'disable'} the keyboard` :
                    'KeyFlip could not change the keyboard',
                output
            );
        }
    }

    _playToggleAnimation() {
        const icon = this._keyboardIcon;
        icon.remove_all_transitions();
        icon.set_scale(1, 1);

        const playFrame = index => {
            if (index >= TOGGLE_SPRING_KEYFRAMES.length)
                return;

            const {scale, duration} = TOGGLE_SPRING_KEYFRAMES[index];
            icon.ease({
                scale_x: scale,
                scale_y: scale,
                duration,
                mode: Clutter.AnimationMode.EASE_OUT_QUAD,
                onComplete: () => playFrame(index + 1),
            });
        };

        playFrame(0);
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
