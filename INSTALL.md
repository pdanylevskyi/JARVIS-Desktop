# Install JARVIS Community Preview

Installers include the desktop app. First-run setup can download and run a local text model on your computer. Voice, vision and advanced server tools require an optional compatible JARVIS Ubuntu backend over SSH. No connection to the author's server is configured. Weights download only after you choose Install and start locally.

## macOS (Apple Silicon)
1. Download the `.dmg` installer and open it.
2. Drag **JARVIS Community.app** into Applications.
3. Open it and follow the hardware setup wizard.

This preview is ad-hoc signed, not Apple notarized. macOS may require approving this specific app in System Settings → Privacy & Security after attempting to open it. Do not disable Gatekeeper. A stable Developer ID signature and notarization are still required for a polished public release and stable macOS permissions across updates. The preview has its own bundle ID and never replaces the owner's private JARVIS app.

## Windows 10/11 (x64)
1. Install Microsoft's Edge WebView2 Runtime and OpenSSH Client if missing.
2. Run the `-setup.exe`; select a shortcut and click Install.
3. Launch JARVIS from Start. No Python or administrator password is needed for the client installer.

The preview EXE is not Authenticode signed; Windows may display a reputation warning. Do not disable protection globally. Uninstall using Settings → Apps.

## Ubuntu / Debian (x64)
Download the `.deb`, then run from its folder:

```sh
sudo apt install ./JARVIS-0.3.0-linux-amd64.deb
```

Launch JARVIS Community from the application menu. Dependencies are installed by apt. Other Linux distributions are not yet packaged. Uninstall with `sudo apt remove jarvis-community`.

## First-run hardware setup
The setup wizard accepts RAM and VRAM in GiB, or scans this computer on request. Enter the specs of the machine that will actually run the model. Review the model and context estimate, then choose **Install and start locally**. Keep the app open while it downloads the runtime and model (several GB; speed depends on your connection). SHA-256 is checked before use. If interrupted, reopen Model setup and retry to resume. Closing the app stops its model process; reopening loads it again.

The default context is 50000 tokens when memory permits; use Context to change it. Model estimates are not guarantees. Choose a smaller model/context if startup fails. Local chat supports document attachments and file tools inside `~/Documents/JARVIS Community`. Voice, images and visual computer control require SSH.

Models, logs and settings are stored in `~/.jarvis-public`. Uninstalling the app preserves these files. The local model API binds only to 127.0.0.1 and requires a per-launch key.

Choose **Save plan** instead if you want to connect to an existing SSH backend.

## Optional SSH connection
1. Prepare your own Ubuntu server with the JARVIS backend in `~/gemma`, its `.desktop-server-venv`, `desktop.worker`, and a running llama-server at localhost:8080. This client release does not provision that backend.
2. Verify its SSH fingerprint with the server owner, then connect once from your terminal: `ssh -i /path/to/your/key user@your-server`. Accept only the verified host key. JARVIS enforces strict host verification.
3. In the app, enter `user@your-server` and select the private key **on your computer**. The key is used by OpenSSH and never uploaded.
4. All clients can use chat and microphone; visual control of the local computer is currently macOS-only. Approve the OS permissions only when using that feature.

Settings are separate in `~/.jarvis-public`. Uninstalling the client preserves settings, server files and downloaded documents. Empty settings are intentional; no personal inventory, server credentials or model weights ship in installers.

## Downloads and checksums
CI builds each installer on its native OS and runs the application's self-test. Maintainers can download installers from the draft GitHub Release linked to the build. Drafts are not visible to public visitors until the maintainer publishes them. Each installer includes a `.sha256` checksum. Checksums detect accidental corruption; they do not replace publisher signing.

Windows dependencies: https://pywebview.flowrl.com/guide/installation
