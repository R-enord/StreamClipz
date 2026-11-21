# Runbook (laptop)

## Start

1. In the StreamClipz folder, double-click `start.bat`.
2. Wait for the line that starts with `Phone, same Wi-Fi:`. Open that address on your phone.
3. If Tailscale is installed and connected, the window also prints a `Phone, anywhere` address.

## Stop

Close the window, or press Ctrl+C in it. The phone cannot connect while it is stopped.

## Where things are

| What | Where |
| --- | --- |
| App code | the StreamClipz folder |
| Login database | `StreamClipz\data\streamclipz.db` |
| Python packages | your normal Python (installed by `start.bat`) |

## Back up (before every update and every change to data)

1. Stop the app.
2. Copy the whole `data` folder to an external drive. Use Copy, not Move.
3. Keep the copy until the new version has run for a few days.

## Update the app

1. Stop the app and back up the `data` folder.
2. Download the latest ZIP (the link is in the README) and extract it into a new folder.
3. Copy the backed-up `data` folder into the new folder so your login is kept.
4. Start the app from the new folder with `start.bat`.
5. Sign in on the phone. If that works, keep the old folder for a few days, then remove it.

## Restore from a backup

1. Stop the app.
2. Rename the broken folder (for example `StreamClipz-broken`). Do not delete it yet.
3. Copy the backup `data` folder into the StreamClipz folder.
4. Start the app.

## The phone cannot connect

- Check that the start window is still open and the laptop is awake.
- Home: the phone must be on the same Wi-Fi as the laptop, not mobile data.
- Away: Tailscale must be connected on both the laptop and the phone.
- The address can change when the Wi-Fi changes. Use the address printed in the current window.
- If Windows Firewall asked about Python, it must be allowed on Private networks.

## Passwords

Password reset is not built yet. Keep your password in a password manager.
