const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const test = require('node:test');
const source = fs.readFileSync('gnome-extension/extension.js', 'utf8')
    .replace(/^import .*;\n/gm, '')
    .replace('export default class KeyFlipExtension', 'class KeyFlipExtension') + '\nglobalThis.Indicator = KeyFlipIndicator;';
function indicator() {
    const context = {
        GObject: {registerClass: cls => cls}, PanelMenu: {Button: class {}},
        Extension: class {}, GLib: {timeout_add: () => 1, timeout_add_seconds: () => 2, source_remove() {}}, Main: {notify() {}},
    };
    vm.runInNewContext(source, context);
    const panel = Object.create(context.Indicator.prototype);
    const settings = {'automatic-mode-switching': true, 'automatic-disable-owned': true};
    Object.assign(panel, {
        _settings: {get_boolean: key => settings[key], set_boolean: (key, value) => settings[key] = value},
        _enabled: false, _externalKeyboardKnown: true, _externalKeyboardIds: new Set(['usb-a']),
        _disconnectChecks: 0, _runAsync: async () => [true, ''], _syncMenu() {},
    });
    return panel;
}
test('last disconnect while busy is retried after operation finishes', async () => {
    const panel = indicator();
    panel._busy = true;
    const changes = [];
    panel._setEnabled = async value => changes.push(value);
    await panel._checkExternalKeyboard();
    await panel._checkExternalKeyboard();
    panel._busy = false;
    await panel._checkExternalKeyboard();
    assert.deepEqual(changes, [true]);
});
test('one keyboard disconnecting while another remains does not restore', async () => {
    const panel = indicator();
    panel._externalKeyboardIds = new Set(['usb-a', 'bt-b']);
    panel._runAsync = async () => [true, 'bt-b'];
    const changes = [];
    panel._setEnabled = async value => changes.push(value);
    await panel._checkExternalKeyboard();
    await panel._checkExternalKeyboard();
    assert.deepEqual(changes, []);
});
test('rapid reconnect cancels pending last-disconnect recovery', async () => {
    const panel = indicator();
    const changes = [];
    panel._setEnabled = async value => changes.push(value);
    await panel._checkExternalKeyboard();
    panel._runAsync = async () => [true, 'usb-a'];
    await panel._checkExternalKeyboard();
    assert.deepEqual(changes, []);
});
