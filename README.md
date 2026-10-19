# JARVIS Community Preview

A cyan/black desktop AI interface for Windows, macOS and Linux. Chat, voice input, file attachments, workshop tools, news, weather and drawing workspace. Connects to **your own** JARVIS Ubuntu backend over SSH.

This is a clean, independent client repository: no private Git history, inventory, credentials, model weights or default server address. The original personal installation is unchanged.

**[Installation and first connection](INSTALL.md)**

| Platform | Installer | Initial target |
|---|---|---|
| Windows | Setup EXE, Start menu, uninstaller | Windows 10/11 x64 |
| macOS | DMG, drag to Applications | Apple Silicon |
| Linux | DEB, application menu, apt dependencies | Ubuntu 22.04+ / Debian-compatible x64 |

## Build
Use Python 3.12 on the target OS:

```sh
python -m pip install -r desktop/requirements.txt pyinstaller==6.20.0
python desktop/build.py
python packaging/package.py
```

Windows packaging additionally requires Inno Setup 6; Linux needs dpkg-deb and the GUI libraries listed in the workflow. CI builds all three platforms and saves installers with SHA-256 files in a draft GitHub Release. No automatic release publication occurs.

On machines without WebGL, the reactor automatically uses a lightweight Canvas renderer.

## Preview limitations
- A compatible Ubuntu backend is required; this is not an all-in-one model installer.
- macOS preview signing is ad-hoc, Windows signing is not yet configured. Publisher certificates/notarization are needed before a frictionless public launch.
- Intel Macs, Linux ARM and non-Debian installers are not yet built.
- Local visual automation is available on macOS only; other platforms retain chat, attachments and microphone input.
- OS permission prompts and SSH host-key verification remain enabled.

## Privacy
No usage analytics. AI requests, microphone recordings and user-attached files go to the configured Ubuntu server. Weather/news features contact their documented public providers; search is performed by your server when enabled. Files on your computer are not automatically uploaded. Public builds use separate `~/.jarvis-public` settings.

## Third-party components
Dependency licenses continue to apply. The bundled DejaVu font license is in `desktop/assets/LICENSE_DEJAVU`. Model licenses are separate; no weights are redistributed here. This preview does not grant an additional open-source license to the application code.
