import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import Clutter from 'gi://Clutter';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as ModalDialog from 'resource:///org/gnome/shell/ui/modalDialog.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

const HELPER = '/usr/libexec/keyflip/keyflip-helper';
const APP = '/usr/libexec/keyflip/app.py';
const SOUND_DIR = '/usr/share/keyflip/sounds';
const SETTINGS_SCHEMA = 'io.github.miflow13.KeyFlip';
const TOGGLE_KEYBINDING = 'toggle-mode-shortcut';

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
class KeyFlipIndicator extends PanelMenu.Button {
    _init(extensionPath) {
        super._init(0.0, 'KeyFlip');
        this.add_style_class_name('keyflip-panel-button');

        this._extensionPath = extensionPath;
        this._settings = new Gio.Settings({schema_id: SETTINGS_SCHEMA});
        this._keyboardIcon = new St.Icon({
            style_class: 'keyflip-keyboard-icon',
        });
        this._keyboardIcon.set_pivot_point(0.5, 0.5);
        this.add_child(this._keyboardIcon);
        this._modeLabel = new PopupMenu.PopupMenuItem('Checking keyboard…', {reactive: false});
        this.menu.addMenuItem(this._modeLabel);
        this._laptopAction = this.menu.addAction('Laptop Mode', () => this._requestEnabled(true));
        this._deskAction = this.menu.addAction('Desk Mode', () => this._requestEnabled(false));
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this.menu.addAction('Open KeyFlip', () => this._openApp());
        this.menu.addAction('Preferences', () => this._runApp('--preferences'));
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this._quitAction = this.menu.addAction('Quit', () => this._quit());
        this._syncMenu();
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
            this._disableDialog?.destroy();
            this._disableDialog = null;
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
            this._enabled = undefined;
            this._keyboardIcon.gicon = null;
            this._keyboardIcon.icon_name = 'dialog-error-symbolic';
            this.accessible_name = `KeyFlip: ${output || 'status unavailable'}`;
            this._syncMenu();
            return;
        }

        this._enabled = output.includes('enabled');
        this._keyboardIcon.icon_name = null;
        this._keyboardIcon.gicon = Gio.icon_new_for_string(
            `${this._extensionPath}/keyboard-${this._enabled ? 'enabled' : 'disabled'}.svg`
        );
        this.accessible_name = `Internal keyboard ${this._enabled ? 'enabled' : 'disabled'}`;
        this._syncMenu();
    }

    _syncMenu() {
        const available = typeof this._enabled === 'boolean';
        this._modeLabel.label.text = !available ? 'Keyboard unavailable' :
            (this._enabled ? 'Laptop Mode active' : 'Desk Mode active');
        const idle = !this._busy && !this._requestPending && !this._quitting;
        const canChange = available && idle;
        this._quitAction.setSensitive(idle && !this._disableDialog);
        this._laptopAction.setSensitive(canChange);
        this._deskAction.setSensitive(canChange);
        this._laptopAction.setOrnament(this._enabled === true ?
            PopupMenu.Ornament.DOT : PopupMenu.Ornament.NONE);
        this._deskAction.setOrnament(this._enabled === false ?
            PopupMenu.Ornament.DOT : PopupMenu.Ornament.NONE);
    }

    _openApp() {
        const app = Shell.AppSystem.get_default().lookup_app('io.github.miflow13.KeyFlip.desktop');
        if (app)
            app.activate();
        else
            Main.notify('KeyFlip could not open', 'Reinstall KeyFlip to restore the application launcher.');
    }

    async _runApp(option) {
        const [success, output] = await this._runAsync(['/usr/bin/python3', APP, option]);
        if (!success)
            Main.notify('KeyFlip could not complete the action', output);
        return success;
    }

    async _quit() {
        if (this._busy || this._requestPending || this._quitting || this._disableDialog)
            return;
        this._quitting = true;
        this._syncMenu();
        const accepted = await this._runApp('--quit');
        if (accepted)
            this._stopBackground();
        if (!this._destroyed) {
            this._quitting = false;
            this._syncMenu();
        }
    }

    _toggle() {
        return this._requestEnabled(!this._enabled);
    }

    async _requestEnabled(enabling) {
        if (this._destroyed || this._busy || this._requestPending || this._quitting || this._disableDialog ||
            typeof this._enabled !== 'boolean' || enabling === this._enabled)
            return;

        // A manual choice ends the current automatic disable cycle.
        this._settings.set_boolean('automatic-disable-owned', false);
        this._requestPending = true;
        this._syncMenu();
        try {
            if (!enabling) {
                const [success, output] = await this._runAsync([HELPER, 'external-list']);
                if (this._destroyed)
                    return;
                if (!success || !output) {
                    this._confirmDisableWithoutExternalKeyboard();
                    return;
                }
            }
            await this._setEnabled(enabling);
        } finally {
            this._requestPending = false;
            if (!this._destroyed)
                this._syncMenu();
        }
    }

    _confirmDisableWithoutExternalKeyboard() {
        const dialog = new ModalDialog.ModalDialog();
        this._disableDialog = dialog;
        dialog.connect('destroy', () => {
            this._disableDialog = null;
        });
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

        if (this._busy || this._requestPending || this._quitting || this._disableDialog)
            return;

        if (connected && this._enabled) {
            this._setEnabled(false, true);
        }
        else if (!connected && wasKnown && wasConnected &&
                 this._settings.get_boolean('automatic-disable-owned') &&
                 !this._enabled && !this._busy)
            this._setEnabled(true, true);
    }

    async _setEnabled(enabling, automatic = false) {
        this._busy = true;
        this._syncMenu();
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
        this._keyboardIcon.opacity = 255;
        await this._refresh();
        if (this._destroyed)
            return;
        this._busy = false;
        this._syncMenu();
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
        this._settings = new Gio.Settings({schema_id: SETTINGS_SCHEMA});
        this._backgroundChangedId = this._settings.connect('changed::background-enabled', () => this._syncBackground());
        this._syncBackground();
    }

    _syncBackground() {
        if (!this._settings.get_boolean('background-enabled')) {
            this._stopBackground();
            return;
        }
        if (this._indicator)
            return;
        this._indicator = new KeyFlipIndicator(this.path);
        Main.panel.addToStatusArea(this.uuid, this._indicator, 0, 'right');
        Main.wm.addKeybinding(
            TOGGLE_KEYBINDING,
            this._settings,
            Meta.KeyBindingFlags.IGNORE_AUTOREPEAT,
            Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW,
            () => this._indicator._toggle()
        );
    }

    _stopBackground() {
        if (!this._indicator)
            return;
        Main.wm.removeKeybinding(TOGGLE_KEYBINDING);
        this._indicator.destroy();
        this._indicator = null;
    }

    disable() {
        if (this._backgroundChangedId) {
            this._settings.disconnect(this._backgroundChangedId);
            this._backgroundChangedId = null;
        }
        this._stopBackground();
        this._settings = null;
    }
}
