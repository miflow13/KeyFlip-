# KeyFlip

![KeyFlip icon](assets/keyflip.png)

# ✨ KeyFlip

> **A tiny Fedora utility ***

**KeyFlip 0.1.0-beta** is a simple GNOME app for safely enabling or disabling a supported laptop’s internal keyboard.

Perfect for laptop-on-a-stand setups, external mechanical keyboards, desk setups, or anyone who has ever rested their hand on their laptop and accidentally typed:

`hjjjjjjjjjjjjjjjj`



KeyFlip works on both **Wayland and X11** and leaves your external USB and Bluetooth keyboards alone.

---

## 💖 Why KeyFlip exists

I wanted to use my external mechanical keyboard with my laptop without constantly bumping keys on the built-in keyboard.

I figured out how to disable the internal keyboard through Linux, made a script for it, and eventually thought:

> okay... why isn't this just a cute little button?

So I made one.

---

## 🤖 AI-assisted

KeyFlip was built with help from AI tools during parts of the coding, debugging, brainstorming, documentation, and learning process.

I'm not interested in pretending otherwise.

AI helped me work through problems, understand unfamiliar concepts, troubleshoot bugs, and occasionally generate code that I could then inspect, test, change, or completely break and fix again. ✨

But AI does **not** independently maintain this project.

I:

- came up with the idea
- chose the direction
- tested the software
- made implementation decisions
- reviewed and modified the code
- broke things
- fixed things
- and remain responsible for what gets released

I'm still actively learning software development, and KeyFlip is part of that process.

My philosophy is basically:

> **Build it → understand it → test it → improve it → repeat.**

AI is one of the tools I use to learn.

It isn't a substitute for understanding what I'm shipping.

If I publish it, **I'm responsible for it.** 💗

---

## 🌸 Requirements

Currently, KeyFlip is primarily built and tested for:

- **Fedora Linux**
- **GNOME**
- Python 3
- GTK 4 Python bindings (`python3-gobject`)
- `polkit`
- `util-linux`
- `systemd`
- a standard **i8042/AT internal keyboard**

KeyFlip works on:

- ✅ Wayland
- ✅ X11
- ✅ External USB keyboards remain untouched
- ✅ Bluetooth keyboards remain untouched

Currently unsupported:

- ❌ Internal USB keyboards
- ❌ Internal I2C keyboards

Support for more hardware is something I'd love to explore as KeyFlip grows.

---

## 🎀 Install the beta

Download and extract:

`keyflip-0.1.0-beta.tar.gz`

Then open a terminal inside the folder and run:

```bash
cd keyflip-0.1.0-beta
sudo ./install.sh
```

Open **KeyFlip** from the GNOME application menu. Running directly from source uses the normal Fedora administrator authorization prompt; the installed application uses the restricted KeyFlip policy described below.

After installation, log out and back in once, then enable the top-bar control:

```bash
gnome-extensions enable keyflip@miflow13.github.io
```

Click the keyboard icon in the GNOME top bar to enable or disable the internal keyboard instantly. The installed Polkit policy permits an active local session to run only KeyFlip's root-owned keyboard helper without another password prompt; it does not grant general passwordless administrator access. The full KeyFlip window remains available from the application menu.

Keep an external keyboard connected before disabling the internal keyboard.

## Run from source

```bash
./keyflip
```

## Command-line helper

From the source directory:

```bash
sudo ./keyflip-helper disable
sudo ./keyflip-helper enable
sudo ./keyflip-helper toggle
./keyflip-helper status
```

For a safe 15-second test:

```bash
sudo ./keyflip-helper test
```

## Build a release archive

```bash
make package
```

The distributable archive and SHA-256 checksum are written to `dist/`.

## Uninstall

From the extracted release or source directory:

```bash
sudo ./uninstall.sh
```

## Recovery

If authorization is cancelled while the internal keyboard is disabled, use an external keyboard and run:

```bash
sudo /usr/local/lib/keyflip/keyflip-helper enable
```

Restarting the computer also restores normal keyboard operation.
