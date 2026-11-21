# Runbook (Windows laptop)

## Where things are

| What | Where |
| --- | --- |
| The app | `C:\Users\<you>\ClipzHub` |
| Your data (login, database, logs) | `C:\Users\<you>\ClipzHub-data` |
| Saved copies of replaced files (from updates) | `C:\Users\<you>\ClipzHub-backups` |
| The older copy, from before the switch | `C:\Users\<you>\StreamClipz`. Delete it once the new one works |

## Start and stop

- **Start:** double-click `start.bat` in ClipzHub. Keep the window open.
- **Stop:** close the window, or press Ctrl+C in it.

## Update (no re-download needed)

1. Double-click `update.bat` in ClipzHub. It downloads the latest version, keeps your data, and saves
   the files it replaces.
2. Double-click `start.bat`.

## Back up your data

1. Stop the app.
2. Copy the `ClipzHub-data` folder to an external drive. Use Copy, not Move.

Do this before any large change.

## Restore a backup

1. Stop the app.
2. Rename `ClipzHub-data` to `ClipzHub-data-broken`. Do not delete it yet.
3. Copy your backup into a new folder named `ClipzHub-data`.
4. Start the app.

## The phone cannot connect

- Check that the start window is open and the laptop is awake.
- At home, the phone must be on the same Wi-Fi as the laptop, not on mobile data.
- Away from home, Tailscale must be connected on both the laptop and the phone.
- Use the address printed in the current window. It can change when the Wi-Fi changes.
- If Windows asked about the firewall, allow Python on Private networks.

## Passwords

Password reset is not built yet. Keep your password in a password manager.
