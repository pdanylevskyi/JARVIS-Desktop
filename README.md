# JARVIS Community Preview

Speech output is currently disabled. Responses are text-only; microphone input remains available. Existing voice-output preferences are ignored.


A cyan/black desktop AI interface for Windows, macOS and Linux. Chat, voice input, file attachments, workshop tools, news, weather and drawing workspace. Run a text model locally, or connect to **your own** compatible JARVIS Ubuntu backend over SSH.

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
- Local mode supports text chat, document attachments, search and file tools. Voice, vision and Mac visual automation require the optional compatible Ubuntu backend.
- macOS preview signing is ad-hoc, Windows signing is not yet configured. Publisher certificates/notarization are needed before a frictionless public launch.
- Intel Macs, Linux ARM and non-Debian installers are not yet built.
- Local visual automation is available on macOS only; other platforms retain chat, attachments and microphone input.
- OS permission prompts and SSH host-key verification remain enabled.

## Privacy
No usage analytics. In local mode, inference stays on this computer. In SSH mode, AI requests, microphone recordings and user-attached files go to the configured Ubuntu server. Weather/news features contact their documented public providers; search contacts external providers when enabled. Files on your computer are not automatically uploaded. Public builds use separate `~/.jarvis-public` settings.

## Third-party components
Dependency licenses continue to apply. The bundled DejaVu font license is in `desktop/assets/LICENSE_DEJAVU`. Model licenses are separate; no weights are redistributed here. This preview does not grant an additional open-source license to the application code.

## Hardware setup (0.3.0)

First launch offers a model-planning wizard: enter RAM/VRAM manually or scan this computer. NVIDIA uses nvidia-smi; Linux AMD uses sysfs; Apple Silicon is reported as unified memory and is never counted twice. An undetected GPU requires manual input. Recommendations target the machine that will run inference, not automatically the client Mac/Windows computer.

The verified catalog includes HauhauCS Qwen3.5 2B/4B/9B/27B Uncensored GGUF variants, only existing Q4_K_M, Q5_K_M, Q6_K and Q8_0 files. Each entry pins its revision, SHA-256, size, source model configuration and context ceiling. The public default is 50000 tokens; memory-limited choices lower it. Maximum context is an estimate including F16 KV cache, runtime reserve and model limits, not a guaranteed benchmark. Choose **Install and start locally** to explicitly download the selected weights and official llama.cpp runtime. Downloads resume and verify pinned SHA-256 checksums. The server listens only on loopback with a random API key. Weights and runtime stay in `~/.jarvis-public`; local file tools use `~/Documents/JARVIS Community`. **Save plan** keeps the optional SSH workflow.

On an updated compatible Ubuntu backend, the Context button changes the active model context with rollback if startup fails. The supported agent range begins at 16384 tokens because its tool schemas and system instructions need space. Changing this shared backend affects every connected client. The interface language can be English or Ukrainian; model/source content is not machine-translated by this selector. Closing the app cancels its active task and stops its owned local model process. The tok/s indicator reports server timings.

The Context dialog includes a synchronized slider and exact number field, from 16384 tokens to the connected model limit. Changes apply only after Apply; moving the slider does not restart inference. Response length settings are unchanged.

Context changes within the currently allocated window apply to subsequent requests without reloading weights. Increasing allocation may still require loading the model. Lowering the logical context does not release allocated RAM. Dictation uses a separate request and remains available while chat is busy; recognized text is appended to the draft for manual submission. Automatic project excerpts are bounded to 12,000 characters, with files still accessible through tools.
