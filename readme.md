**FEDORA LINUX — EVERYDAY CHEAT SHEET**

For standard Fedora Workstation/KDE. Atomic editions such as Silverblue use different system update commands.

**Basics**
- `sudo command` → run as administrator
- `command --help` → quick help
- `man command` → manual; press `q` to exit
- `clear` → clear terminal

**Move around**
- `pwd` → show current folder
- `ls` → list files
- `ls -lah` → detailed list, including hidden files
- `cd folder` → enter folder
- `cd ..` → go up one folder
- `cd ~` → go home
- `cd -` → return to previous folder

**Files & folders**
- `mkdir folder` → create folder
- `touch file.txt` → create empty file
- `cp file copy` → copy file
- `cp -r folder copy` → copy folder
- `mv old new` → move or rename
- `rm -i file` → delete file, asking first
- `rmdir folder` → delete empty folder
- `cat file.txt` → display file
- `less file.txt` → scroll through file; `q` quits
- `nano file.txt` → edit file, if Nano is installed

**Install & update software**
- `sudo dnf upgrade --refresh` → update system packages
- `dnf search word` → find packages
- `dnf info package` → package details
- `sudo dnf install package` → install
- `sudo dnf remove package` → uninstall
- `flatpak update` → update Flatpak apps
- `flatpak list` → list installed Flatpaks

**System & network**
- `cat /etc/fedora-release` → Fedora version
- `df -h` → disk space
- `free -h` → memory usage
- `top` → running processes; `q` quits
- `ip -br addr` → IP addresses
- `nmcli device status` → network status
- `systemctl --failed` → failed services
- `reboot` → restart
- `poweroff` → shut down

**Terminal shortcuts**
- `Tab` → complete command or filename
- `↑ / ↓` → previous/next command
- `Ctrl+C` → stop current command
- `Ctrl+L` → clear screen
- `Ctrl+R` → search command history
- `Ctrl+Shift+C / V` → copy/paste in most terminals

**Remember**
- Replace `file`, `folder`, and `package` with actual names.
- Names are case-sensitive: `Notes` ≠ `notes`.
- Quote spaces: `cd "My Folder"`.
- `sudo` passwords stay invisible while typing.
- `rm` deletes directly; it does not use the Trash.